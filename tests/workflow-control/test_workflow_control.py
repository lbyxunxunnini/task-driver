import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/workflow_control.py'
spec = importlib.util.spec_from_file_location('workflow_control', SCRIPT)
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


def state(**updates):
    value = {'task_id': 'task-a', 'phase': 'discussion', 'status': 'continue',
             'next_action': '继续讨论未决事项', 'decisions': [{'id': 'd1', 'subject': '范围', 'status': 'pending'}],
             'gates': {'plan': None, 'goals': None, 'execution': None, 'subagents': None},
             'plan': {'presented': False}, 'coverage_checked': True, 'plan_requested': True, 'plan_request_source': '用户明确要求计划'}
    value.update(updates)
    if 'gates' in updates and 'subagents' not in value['gates']:
        value['gates'] = dict(value['gates'], subagents='测试中的用户明确选择')
    if (isinstance(value.get('plan'), dict) and isinstance(value.get('goals'), dict) and
            value['plan'].get('presented') is True and value['goals'].get('presented') is True):
        shared = (value['plan'].get('presentation_id') or
                  value['goals'].get('presentation_id') or
                  value['plan'].get('evidence'))
        if isinstance(shared, str) and shared.strip():
            value['plan'] = dict(value['plan'], presentation_id=shared)
            value['goals'] = dict(value['goals'], presentation_id=shared)
    return value


def semantic_review(kind, decision_id=None, reviewer='main', status='pass', checks=None):
    defaults = {
        'decision': {
            'target_is_current': True,
            'not_already_decided': True,
            'not_delegated': True,
            'answerable_now': True,
            'single_question': True,
            'no_trailing_content': True,
            'incomplete_plan_delivered': True,
        },
        'plan_transition': {
            'transition_intent': True,
            'no_blocking_pending_decisions': True,
            'single_question': True,
            'no_trailing_content': True,
        },
        'waived': {
            'waiver_source_is_explicit': True,
            'no_user_question': True,
            'no_trailing_content': True,
        },
    }
    result = {
        'reviewer': reviewer,
        'status': status,
        'target': kind,
        'source': '测试语义复核',
        'checks': dict(defaults[kind] if checks is None else checks),
    }
    if decision_id is not None:
        result['decision_id'] = decision_id
    if reviewer == 'independent':
        result['review_id'] = 'review-test'
        result['authorization_source'] = '测试授权'
    return result


def handoff(kind, decision_id=None, review=None, **review_updates):
    value = {'kind': kind}
    if decision_id is not None:
        value['decision_id'] = decision_id
    value['semantic_review'] = review or semantic_review(kind, decision_id, **review_updates)
    return value


def interruption(**updates):
    frame = {'id':'temp-1', 'request':'查找官网证据', 'source':'用户新请求',
             'status':'continue', 'next_action':'查询官网'}
    frame.update(updates)
    return frame


class ControlTests(unittest.TestCase):
    def test_execution_requires_scope_and_subagent_evidence(self):
        s = state(phase='execution', decisions=[], plan={'presented': True, 'evidence': '计划消息'},
                  goals={'presented': True, 'evidence': '目标消息'},
                  gates={'plan': '用户第 2 轮', 'goals': '用户第 2 轮', 'execution': None})
        self.assertIn('execution evidence required for execution or later', controller.validate(s))
        s['gates']['execution'] = '用户第 2 轮'
        self.assertEqual([], controller.validate(s))
        s['gates'].pop('subagents')
        self.assertIn('subagents evidence required for execution or later', controller.validate(s))
        s['gates']['subagents'] = '用户选择不启用子代理'
        self.assertEqual([], controller.validate(s))

    def test_read_only_operation_check_does_not_require_subagent_setting(self):
        s = state(phase='execution', decisions=[], plan={'presented': True, 'evidence': '计划消息'},
                  goals={'presented': True, 'evidence': '目标消息'},
                  gates={'plan': '计划确认', 'goals': '目标确认', 'execution': None, 'subagents': None},
                  operations=[{'id': 'op1', 'reference': '原作业', 'status': 'unknown',
                               'side_effect': True, 'blocks_next': True}])
        self.assertEqual('check_operation', controller.route(s)['action'])

    def test_waiting_read_only_check_does_not_release_unauthorized_independent_action(self):
        s = state(phase='execution', status='wait_tool', wait_reason='等待原作业', decisions=[],
                  plan={'presented': True, 'evidence': '计划消息'},
                  goals={'presented': True, 'evidence': '目标消息'},
                  gates={'plan': '计划确认', 'goals': '目标确认', 'execution': None, 'subagents': None},
                  independent_action='修改业务文件',
                  operations=[{'id': 'op1', 'reference': '原作业', 'status': 'unknown',
                               'side_effect': True, 'blocks_next': False, 'independent_of_wait': True}])
        result = controller.route(s)
        self.assertEqual('wait_tool', result['action'])
        self.assertEqual(['原作业'], result['independent_checks'])
        self.assertNotIn('independent_action', result)
        s['gates'].update(execution='用户授权范围', subagents='用户选择不开启')
        self.assertEqual('修改业务文件', controller.route(s)['independent_action'])

    def test_read_only_verification_keeps_independent_action_without_execution_gates(self):
        s = state(phase='verification', status='wait_user', wait_reason='等待设备反馈',
                  wait_evidence='已展示验收问题', execution_occurred=False, decisions=[],
                  plan={'presented': True, 'evidence': '计划消息'},
                  independent_action='只读核对现有材料',
                  gates={'plan': None, 'goals': None, 'execution': None, 'subagents': None})
        self.assertEqual('只读核对现有材料', controller.route(s)['independent_action'])

    def test_partial_and_duplicate_decisions(self):
        s = state(status='wait_user', wait_reason='等待验收决定', wait_evidence='上一条消息的验收问题', decisions=[{'id': '1', 'subject': '范围', 'status': 'decided', 'value': '用户选定范围', 'source': '用户第 2 轮'},
                                                  {'id': '2', 'subject': '验收', 'status': 'pending'}])
        self.assertEqual([], controller.validate(s))
        s['decisions'][1]['id'] = '1'
        self.assertIn('decision id missing or duplicated', controller.validate(s))

    def test_delegation_requires_a_decision_before_closure_or_execution(self):
        s = state(decisions=[{'id':'d1', 'subject':'备份策略', 'status':'delegated', 'source':'用户委托'}])
        self.assertEqual('repair_state', controller.route(s)['action'])
        self.assertIn('delegated item requires its actual value', controller.validate(s))
        s['decisions'][0]['status'] = 'pending'
        s['plan_requested'] = False
        self.assertEqual('resolve_pending', controller.route(s)['action'])
        s['decisions'][0].update(status='delegated', value='保留一份可恢复备份')
        s['plan_requested'] = True
        self.assertEqual('present_plan', controller.route(s)['action'])
        s.update(phase='execution', plan={'presented':True, 'evidence':'计划', 'presentation_id':'委托展示'},
                 goals={'presented':True, 'evidence':'目标', 'presentation_id':'委托展示'},
                 gates={'plan':'委托方案', 'goals':'委托目标', 'execution':'执行授权', 'subagents':'用户选择不开启'})
        self.assertEqual('continue_current_phase', controller.route(s)['action'])
        s['decisions'][0].pop('value')
        self.assertEqual('repair_state', controller.route(s)['action'])

    def test_waiting_requires_a_previously_presented_question(self):
        s = state(status='wait_user', wait_reason='等待回答')
        self.assertIn('wait_user requires reference to already presented question', controller.validate(s))
        self.assertEqual('repair_state', controller.route(s)['action'])

    def test_wait_for_authorization_and_deferred_item(self):
        self.assertEqual([], controller.validate(state(status='wait_user', wait_reason='等待执行许可', wait_evidence='上一条消息的执行许可问题', decisions=[])))
        s = state(status='complete', completion_evidence='交付回执', plan_required=False, plan_requested=False, plan_waiver_source='已有成果满足用户目标', decisions=[{'id':'later','subject':'后续事项','status':'pending','blocks_completion':False,'nonblocking_reason':'用户同意延期且不影响本次目标'}])
        self.assertEqual([], controller.validate(s))

    def test_unpresented_plan_advances_only_after_discussion_is_ready(self):
        s = state()
        self.assertEqual('present_incomplete_plan', controller.route(s)['action'])
        s['plan'].update(draft_presented=True, draft_evidence='上一轮已发送草案', draft_for_request=s['plan_request_source'])
        self.assertEqual('resolve_pending', controller.route(s)['action'])
        s['decisions'][0].update(status='decided', value='用户选定范围', source='用户回答')
        self.assertEqual('present_plan', controller.route(s)['action'])
        s['plan_requested'] = False
        self.assertEqual('request_plan_transition', controller.route(s)['action'])
        s.update(status='paused', wait_reason='用户暂停')
        self.assertEqual('paused', controller.route(s)['action'])

    def test_plan_request_with_pending_decision_requires_incomplete_plan_draft(self):
        s = state(decisions=[{
            'id': 'd1',
            'subject': '存储方案',
            'status': 'pending',
            'question': '你希望采用方案 A 还是方案 B？',
        }])
        self.assertEqual('present_incomplete_plan', controller.route(s)['action'])
        self.assertIn(
            'discussion final must deliver the incomplete plan draft',
            controller.validate_discussion_final(
                s,
                '分析完成。\n\n你希望采用方案 A 还是方案 B？',
                handoff('decision', 'd1'),
            ),
        )
        s['plan'].update(
            draft_presented=True,
            draft_evidence='本轮已交付的缺口草案',
            draft_for_request=s['plan_request_source'],
        )
        missing_review = handoff('decision', 'd1')
        missing_review['semantic_review']['checks']['incomplete_plan_delivered'] = False
        self.assertIn(
            'discussion semantic review check failed: incomplete_plan_delivered',
            controller.validate_discussion_final(
                s,
                '带缺口的讨论稿：先确认存储方案。\n\n你希望采用方案 A 还是方案 B？',
                missing_review,
            ),
        )
        self.assertEqual([], controller.validate_discussion_final(
            s,
            '带缺口的讨论稿：先确认存储方案。\n\n你希望采用方案 A 还是方案 B？',
            handoff('decision', 'd1'),
        ))

    def test_discussion_after_an_answer_routes_to_next_question_or_closure(self):
        answered = {'id': 'd1', 'subject': '当前选择', 'status': 'decided', 'value': '已选择', 'source': '用户回答'}
        pending = {'id': 'd2', 'subject': '下一事项', 'status': 'pending'}
        s = state(plan_requested=False, decisions=[answered, pending], next_action='讨论下一事项')
        self.assertEqual('resolve_pending', controller.route(s)['action'])
        s['decisions'] = [answered]
        self.assertEqual('request_plan_transition', controller.route(s)['action'])
        s.update(plan_requested=True, plan_request_source='用户要求计划')
        self.assertEqual('present_plan', controller.route(s)['action'])
        s.update(status='wait_user', wait_reason='等待用户决定', wait_evidence='已展示的问题')
        self.assertEqual('wait_user', controller.route(s)['action'])

    def test_discussion_final_must_end_with_one_question(self):
        s = state(plan_requested=False, decisions=[{
            'id': 'd1',
            'subject': '范围',
            'status': 'pending',
            'question': '范围上你希望采用方案 A 还是方案 B？',
        }])
        final_handoff = handoff('decision', 'd1')
        self.assertIn(
            'discussion final reply must end with exactly one question',
            controller.validate_discussion_final(s, '已完成分析，方案整理如上。', final_handoff),
        )
        self.assertIn(
            'discussion final reply must end with exactly one question',
            controller.validate_discussion_final(
                s, '范围上你希望采用方案 A 还是方案 B？\n\n1. 方案 A\n2. 方案 B', final_handoff
            ),
        )
        self.assertEqual(
            [],
            controller.validate_discussion_final(
                s, '已完成分析。\n\n范围上你希望采用方案 A 还是方案 B？', final_handoff
            ),
        )

    def test_discussion_final_without_pending_asks_to_end_and_present_plan(self):
        s = state(plan_requested=False, decisions=[])
        final_handoff = handoff('plan_transition')
        self.assertIn(
            'discussion semantic review did not pass',
            controller.validate_discussion_final(
                s,
                '分析已经完成。\n\n你还想补充其他资料吗？',
                handoff('plan_transition', status='fail'),
            ),
        )
        self.assertEqual(
            [],
            controller.validate_discussion_final(
                s,
                '分析已经完成。\n\n现在结束讨论，让我一起展示正式计划和目标吗？',
                final_handoff,
            ),
        )

    def test_discussion_final_can_be_explicitly_waived(self):
        paused = state(status='paused', wait_reason='用户暂停', plan_requested=False)
        self.assertIn('discussion question waiver requires source', controller.validate_discussion_final(
            paused, '已按你的要求暂停。', handoff('waived')
        ))
        paused['discussion_question_waiver_source'] = '用户明确要求暂停'
        self.assertEqual([], controller.validate_discussion_final(
            paused, '已按你的要求暂停。', handoff('waived')
        ))
        self.assertIn(
            'discussion waiver final must not add a question',
            controller.validate_discussion_final(
                paused, '已按你的要求暂停。还有问题吗？', handoff('waived')
            ),
        )
        complete = state(
            status='complete',
            plan_required=False,
            plan_requested=False,
            plan_waiver_source='已有结果满足用户目标',
            completion_evidence='结果已交付',
            discussion_question_waiver_source='用户明确结束任务',
            decisions=[],
        )
        self.assertIn(
            'discussion waiver final must not add a question',
            controller.validate_discussion_final(
                complete, '任务已完成。还有问题吗？', handoff('waived')
            ),
        )
        local_only = state(
            plan_requested=False,
            local_only=True,
            local_done=True,
            discussion_question_waiver_source='用户要求本轮只解释且暂不追问',
        )
        self.assertEqual([], controller.validate_discussion_final(
            local_only, '已按你的要求解释。', handoff('waived')
        ))
        self.assertIn('discussion final reply required', controller.validate_discussion_final(
            local_only, '   ', handoff('waived')
        ))
        self.assertIn('discussion question waiver requires source', controller.validate(state(
            plan_requested=False,
            discussion_question_waiver_source='',
        )))

    def test_discussion_final_can_stop_for_explicit_round_scope(self):
        s = state(
            plan_requested=False,
            scope_limited=True,
            scope_limited_source='用户明确要求本轮只交付设计稿',
        )
        self.assertEqual([], controller.validate_discussion_final(
            s, '设计稿已按本轮范围交付。', handoff('waived')
        ))
        self.assertEqual('scope_complete', controller.route(s)['action'])
        presented = state(
            plan_requested=False,
            scope_limited=True,
            scope_limited_source='用户明确要求本轮只交付设计稿',
            plan={'presented': True, 'evidence': '计划'},
            goals={'presented': True, 'evidence': '目标'},
        )
        self.assertEqual('scope_complete', controller.route(presented)['action'])
        self.assertEqual([], controller.validate_discussion_final(
            presented, '本轮指定内容已交付。', handoff('waived')
        ))
        local = state(
            plan_requested=False,
            scope_limited=True,
            scope_limited_source='用户明确要求本轮只交付局部结果',
            local_only=True,
            local_done=True,
        )
        self.assertEqual('local_complete', controller.route(local)['action'])
        self.assertEqual([], controller.validate_discussion_final(
            local, '局部结果已交付。', handoff('waived')
        ))
        paused = state(
            status='paused',
            wait_reason='用户暂停',
            plan_requested=False,
            scope_limited=True,
            scope_limited_source='用户明确要求本轮暂停',
        )
        self.assertEqual('paused', controller.route(paused)['action'])
        self.assertEqual([], controller.validate_discussion_final(
            paused, '已暂停。', handoff('waived')
        ))
        s.pop('scope_limited_source')
        self.assertIn('scope limited source required', controller.validate(s))

    def test_scope_limited_does_not_bypass_activity_or_waiting(self):
        s = state(
            status='wait_tool',
            wait_reason='等待接口',
            plan_requested=False,
            scope_limited=True,
            scope_limited_source='用户明确要求本轮只交付设计稿',
        )
        self.assertIn(
            'discussion final cannot bypass active interruption or blocking state with scoped stop',
            controller.validate_discussion_final(s, '设计稿已交付。', handoff('waived')),
        )
        interrupted = state(
            plan_requested=False,
            scope_limited=True,
            scope_limited_source='用户明确要求本轮只交付设计稿',
            interruptions=[interruption(status='complete', result_evidence='临时结果已交付',
                                         resume_point={'status': 'continue', 'next_action': '返回原任务',
                                                       'phase': 'discussion'})],
        )
        self.assertIn(
            'discussion final cannot bypass active interruption or blocking state with scoped stop',
            controller.validate_discussion_final(interrupted, '设计稿已交付。', handoff('waived')),
        )
        local = state(
            plan_requested=False,
            local_only=True,
            local_done=False,
            scope_limited=True,
            scope_limited_source='用户明确要求本轮只交付设计稿',
        )
        self.assertIn(
            'discussion final cannot bypass active interruption or blocking state with scoped stop',
            controller.validate_discussion_final(local, '设计稿已交付。', handoff('waived')),
        )
        uncovered = state(
            plan_requested=False,
            coverage_checked=False,
            scope_limited=True,
            scope_limited_source='用户明确要求本轮只交付设计稿',
        )
        self.assertIn(
            'discussion final cannot bypass active interruption or blocking state with scoped stop',
            controller.validate_discussion_final(uncovered, '设计稿已交付。', handoff('waived')),
        )
        plan_only = state(
            plan_requested=True,
            plan_request_source='用户要求计划',
            decisions=[],
            scope_limited=True,
            scope_limited_source='用户明确要求本轮只交付计划',
        )
        self.assertIn(
            'discussion final cannot bypass active interruption or blocking state with scoped stop',
            controller.validate_discussion_final(plan_only, '计划已交付。', handoff('waived')),
        )

    def test_scope_limited_waiver_cannot_persist_after_resume(self):
        previous = state(
            status='paused',
            wait_reason='用户暂停',
            plan_requested=False,
            scope_limited=True,
            scope_limited_source='用户明确要求本轮只交付设计稿',
        )
        current = dict(previous, status='continue', resume_source='用户要求继续')
        self.assertIn(
            'scope limited waiver cannot persist across resume',
            controller.validate_transition(previous, current),
        )
        continued = dict(current, status='continue')
        next_turn = dict(continued, next_action='继续另一个事项')
        self.assertEqual(
            [],
            controller.validate_transition(continued, continued),
        )
        self.assertIn(
            'scope limited waiver cannot persist across resume',
            controller.validate_transition(continued, next_turn),
        )
        decision_changed = copy.deepcopy(continued)
        decision_changed['decisions'] = [
            {'id': 'd1', 'subject': '范围', 'status': 'decided',
             'value': '已选择', 'source': '用户回答'}
        ]
        self.assertIn(
            'scope limited waiver cannot persist across resume',
            controller.validate_transition(continued, decision_changed),
        )

    def test_discussion_final_requires_semantic_review_and_matching_decision(self):
        s = state(plan_requested=False, decisions=[
            {
                'id': 'd1',
                'subject': '存储方案',
                'status': 'pending',
                'question': '你希望采用哪种存储方案？',
            },
        ])
        self.assertIn(
            'discussion semantic review did not pass',
            controller.validate_discussion_final(
                s,
                '分析已经完成。\n\n你午饭想吃什么？',
                handoff('decision', 'd1', status='fail'),
            ),
        )
        self.assertIn(
            'discussion decision handoff requires a matching pending decision_id',
            controller.validate_discussion_final(
                s,
                '分析已经完成。\n\n你希望采用哪种存储方案？',
                handoff('decision', 'missing'),
            ),
        )
        self.assertIn(
            'discussion semantic review target must match handoff kind',
            controller.validate_discussion_final(
                s,
                '分析已经完成。\n\n你希望采用哪种存储方案？',
                handoff('decision', 'd1', review=semantic_review('plan_transition')),
            ),
        )
        self.assertIn(
            'discussion semantic review required',
            controller.validate_discussion_final(
                s,
                '分析已经完成。\n\n你希望采用哪种存储方案？',
                {'kind': 'decision', 'decision_id': 'd1'},
            ),
        )
        self.assertEqual(
            [],
            controller.validate_discussion_final(
                s,
                '分析已经完成。\n\n存储上你更想采用哪一种方案？',
                handoff('decision', 'd1'),
            ),
        )

    def test_semantic_review_requires_kind_specific_checks_and_valid_reviewer(self):
        s = state(plan_requested=False, decisions=[{
            'id': 'd1',
            'subject': '存储方案',
            'status': 'pending',
            'question': '你希望采用哪种存储方案？',
        }])
        reviewed = handoff('decision', 'd1', reviewer='independent')
        self.assertEqual([], controller.validate_discussion_final(
            s, '分析已经完成。\n\n你希望采用哪种存储方案？', reviewed
        ))
        reviewed['semantic_review']['reviewer'] = 'self'
        self.assertIn(
            'discussion semantic review reviewer must be main or independent',
            controller.validate_discussion_final(
                s, '分析已经完成。\n\n你希望采用哪种存储方案？', reviewed
            ),
        )
        reviewed['semantic_review']['reviewer'] = 'independent'
        reviewed['semantic_review'].pop('review_id')
        self.assertIn(
            'discussion semantic review independent review_id required',
            controller.validate_discussion_final(
                s, '分析已经完成。\n\n你希望采用哪种存储方案？', reviewed
            ),
        )
        reviewed['semantic_review']['review_id'] = 'review-test'
        reviewed['semantic_review'].pop('authorization_source')
        self.assertIn(
            'discussion semantic review independent authorization_source required',
            controller.validate_discussion_final(
                s, '分析已经完成。\n\n你希望采用哪种存储方案？', reviewed
            ),
        )
        missing_check = handoff('decision', 'd1')
        missing_check['semantic_review']['checks']['not_delegated'] = False
        self.assertIn(
            'discussion semantic review check failed: not_delegated',
            controller.validate_discussion_final(
                s, '分析已经完成。\n\n你希望采用哪种存储方案？', missing_check
            ),
        )
        transition = handoff('plan_transition')
        transition['semantic_review']['checks']['transition_intent'] = False
        transition_state = state(plan_requested=False, decisions=[])
        self.assertIn(
            'discussion semantic review check failed: transition_intent',
            controller.validate_discussion_final(
                transition_state,
                '分析已经完成。\n\n现在展示正式计划与目标吗？',
                transition,
            ),
        )

    def test_discussion_final_cannot_bypass_pending_or_unchecked_coverage(self):
        pending = state(plan_requested=False, decisions=[
            {
                'id': 'd1',
                'subject': '存储方案',
                'status': 'pending',
                'question': '你希望采用哪种存储方案？',
            },
        ])
        self.assertIn(
            'discussion plan transition cannot bypass pending decisions',
            controller.validate_discussion_final(
                pending,
                '分析已经完成。\n\n是否结束讨论并开始展示正式计划与目标？',
                handoff('plan_transition'),
            ),
        )
        unchecked = state(plan_requested=False, decisions=[], coverage_checked=False)
        errors = controller.validate_discussion_final(
            unchecked,
            '分析已经完成。\n\n是否结束讨论并开始展示正式计划与目标？',
            handoff('plan_transition'),
        )
        self.assertIn('discussion plan transition conflicts with next action: check_coverage', errors)
        self.assertIn('discussion final requires coverage_checked before handoff', errors)
        pending_unchecked = state(
            plan_requested=True,
            plan_request_source='用户要求计划',
            coverage_checked=False,
            decisions=pending['decisions'],
        )
        errors = controller.validate_discussion_final(
            pending_unchecked,
            '以下是带缺口的讨论稿。\n\n你希望采用哪种存储方案？',
            handoff('decision', 'd1'),
        )
        self.assertIn('discussion final requires coverage_checked before handoff', errors)

    def test_discussion_final_rejects_active_interruption_and_waiting_plan_handoff(self):
        interrupted = state(plan_requested=False, decisions=[], interruptions=[interruption()])
        errors = controller.validate_discussion_final(
            interrupted,
            '临时请求已经处理。\n\n是否结束讨论并开始展示正式计划与目标？',
            handoff('plan_transition'),
        )
        self.assertIn('discussion plan transition conflicts with next action: handle_interruption', errors)
        waiting = state(status='wait_tool', wait_reason='等待外部接口', plan_requested=False, decisions=[])
        errors = controller.validate_discussion_final(
            waiting,
            '接口仍在查询。\n\n是否结束讨论并开始展示正式计划与目标？',
            handoff('plan_transition'),
        )
        self.assertIn('discussion plan transition conflicts with next action: wait_tool', errors)

    def test_discussion_final_accepts_semantically_equivalent_pending_question(self):
        s = state(
            status='wait_tool',
            wait_reason='等待外部接口',
            wait_evidence='已说明等待原因',
            plan_requested=False,
            decisions=[{
                'id': 'd1',
                'subject': '阻塞处理',
                'status': 'pending',
                'question': '你希望继续等待接口，还是先调整当前范围？',
            }],
        )
        self.assertEqual([], controller.validate_discussion_final(
            s,
            '接口仍在查询。\n\n现在先等接口，还是把范围调整一下？',
            handoff('decision', 'd1'),
        ))

    def test_discussion_question_waiver_does_not_survive_resume(self):
        previous = state(
            status='paused',
            wait_reason='用户暂停',
            discussion_question_waiver_source='用户明确要求暂停',
            plan_requested=False,
        )
        current = dict(
            previous,
            status='continue',
            resume_source='用户要求继续',
        )
        self.assertIn(
            'discussion question waiver cannot persist across resume',
            controller.validate_transition(previous, current),
        )
        local_previous = state(
            plan_requested=False,
            local_only=True,
            local_done=True,
            discussion_question_waiver_source='用户要求本轮只解释',
        )
        local_resumed = dict(
            local_previous,
            local_only=False,
            local_done=False,
            next_action='返回原任务继续讨论',
        )
        self.assertIn(
            'discussion question waiver cannot persist across resume',
            controller.validate_transition(local_previous, local_resumed),
        )

    def test_discussion_plan_transition_rejects_failed_semantic_review(self):
        s = state(plan_requested=False, decisions=[])
        errors = controller.validate_discussion_final(
            s,
            '分析完成。\n\n是否不要结束讨论，也不要展示计划和目标？',
            handoff('plan_transition', status='fail'),
        )
        self.assertIn('discussion semantic review did not pass', errors)

    def test_semantic_review_rejects_conflicting_or_negated_questions(self):
        decision = state(plan_requested=False, decisions=[{
            'id': 'd1',
            'subject': '范围',
            'status': 'pending',
            'question': '你希望采用方案 A 还是方案 B？',
        }])
        self.assertIn(
            'discussion semantic review did not pass',
            controller.validate_discussion_final(
                decision,
                '分析完成。\n\n请忽略下面这个问题：你希望采用方案 A 还是方案 B？',
                handoff('decision', 'd1', status='fail'),
            ),
        )
        self.assertIn(
            'discussion semantic review did not pass',
            controller.validate_discussion_final(
                decision,
                '分析完成。\n\n❌你希望采用方案 A 还是方案 B？',
                handoff('decision', 'd1', status='fail'),
            ),
        )
        transition = state(plan_requested=False, decisions=[])
        self.assertIn(
            'discussion semantic review did not pass',
            controller.validate_discussion_final(
                transition,
                '分析完成。\n\n请先不要结束讨论：是否结束讨论并开始展示正式计划与目标？',
                handoff('plan_transition', status='fail'),
            ),
        )

    def test_discussion_final_rejects_earlier_questions(self):
        s = state(plan_requested=False, decisions=[])
        self.assertIn(
            'discussion final reply must end with exactly one question',
            controller.validate_discussion_final(
                s,
                '方案 A 可以吗？方案 B 可以吗？\n\n是否结束讨论并开始展示正式计划与目标？',
                handoff('plan_transition'),
            ),
        )
        self.assertEqual(
            [],
            controller.validate_discussion_final(
                s,
                '资料链接：https://example.com/?id=1\n\n是否结束讨论并开始展示正式计划与目标？',
                handoff('plan_transition'),
            ),
        )
        self.assertEqual(
            [],
            controller.validate_discussion_final(
                s,
                '资料链接：[页面](docs/page?id=1&view=full)\n\n是否结束讨论并开始展示正式计划与目标？',
                handoff('plan_transition'),
            ),
        )
        self.assertEqual(
            [],
            controller.validate_discussion_final(
                s,
                '[doc]: docs/page?id=1&view=full\n\n是否结束讨论并开始展示正式计划与目标？',
                handoff('plan_transition'),
            ),
        )
        self.assertEqual(
            [],
            controller.validate_discussion_final(
                s,
                '页面 docs/page?id=1，用户问“要不要做？”\n\n是否结束讨论并开始展示正式计划与目标？',
                handoff('plan_transition'),
            ),
        )
        self.assertEqual(
            [],
            controller.validate_discussion_final(
                s,
                '用户问「要不要做？」\n\n是否结束讨论并开始展示正式计划与目标？',
                handoff('plan_transition'),
            ),
        )
        self.assertEqual(1, controller.count_questions_outside_code('是否采用 API?'))
        self.assertEqual(2, controller.count_questions_outside_code('先确认 API?, 还是直接继续？'))
        self.assertEqual(0, controller.count_questions_outside_code('接口 /api?page=2'))
        self.assertEqual(0, controller.count_questions_outside_code('用户问「要不要做？」'))
        self.assertEqual(0, controller.count_questions_outside_code("用户问‘要不要做？’"))
        self.assertIn(
            'discussion semantic review did not pass',
            controller.validate_discussion_final(
                s,
                '分析完成。\n\n❌是否结束讨论并开始展示正式计划与目标？',
                handoff('plan_transition', status='fail'),
            ),
        )

    def test_discussion_final_cannot_bypass_blocking_operation(self):
        operation = {
            'id': 'job',
            'reference': '原操作',
            'status': 'unknown',
            'side_effect': True,
            'blocks_next': True,
        }
        decision = state(
            status='wait_user',
            wait_reason='等待用户决定',
            wait_evidence='已展示问题',
            plan_requested=False,
            decisions=[{
                'id': 'd1',
                'subject': '范围',
                'status': 'pending',
                'question': '你希望采用方案 A 还是方案 B？',
            }],
            operations=[operation],
        )
        self.assertIn(
            'discussion final blocked by unresolved operation: 原操作',
            controller.validate_discussion_final(
                decision,
                '分析完成。\n\n你希望采用方案 A 还是方案 B？',
                handoff('decision', 'd1'),
            ),
        )
        local = state(
            plan_requested=False,
            local_only=True,
            local_done=True,
            discussion_question_waiver_source='用户要求本轮只解释',
            operations=[operation],
        )
        self.assertIn(
            'discussion final blocked by unresolved operation: 原操作',
            controller.validate_discussion_final(local, '解释完成。', handoff('waived')),
        )

    def test_final_cli_checks_the_actual_draft_reply(self):
        s = state(plan_requested=False, decisions=[{
            'id': 'd1',
            'subject': '范围',
            'status': 'pending',
            'question': '范围上你希望采用方案 A 还是方案 B？',
        }])
        valid = {
            'state': s,
            'draft_reply': '分析结果如下。\n\n范围上你希望采用方案 A 还是方案 B？',
            'discussion_handoff': handoff('decision', 'd1'),
        }
        p = subprocess.run([sys.executable, str(SCRIPT), 'final', '--json', json.dumps(valid)],
                           capture_output=True, text=True, check=True)
        self.assertTrue(json.loads(p.stdout)['ok'])
        invalid = {
            'state': s,
            'draft_reply': '分析结果如下。',
            'discussion_handoff': handoff('decision', 'd1'),
        }
        p = subprocess.run([sys.executable, str(SCRIPT), 'final', '--json', json.dumps(invalid)],
                           capture_output=True, text=True)
        self.assertNotEqual(0, p.returncode)
        self.assertFalse(json.loads(p.stdout)['ok'])
        missing_reply = {'state': dict(s, phase='planning')}
        p = subprocess.run([sys.executable, str(SCRIPT), 'final', '--json', json.dumps(missing_reply)],
                           capture_output=True, text=True)
        self.assertNotEqual(0, p.returncode)
        self.assertIn('draft_reply', json.loads(p.stdout)['errors'][0])

    def test_unchecked_coverage_does_not_mean_discussion_is_done(self):
        s = state(plan_requested=False, decisions=[], coverage_checked=False)
        self.assertEqual('check_coverage', controller.route(s)['action'])

    def test_planning_cannot_stop_before_presenting_plan(self):
        s = state(phase='planning', decisions=[], plan_requested=False, next_action='暂时结束')
        self.assertEqual('request_plan_transition', controller.route(s)['action'])
        s['plan_requested'] = True
        self.assertEqual('present_plan', controller.route(s)['action'])
        s.update(status='paused', wait_reason='用户暂停')
        self.assertEqual('paused', controller.route(s)['action'])

    def test_nonblocking_requires_reason(self):
        s = state(decisions=[{'id':'later','subject':'范围','status':'pending','blocks_plan':False}])
        self.assertIn('nonblocking pending decision requires reason', controller.validate(s))

    def test_nonblocking_completion_does_not_imply_plan_unaffected(self):
        item = {'id': 'later', 'subject': '待定事项', 'status': 'pending', 'blocks_completion': False, 'nonblocking_reason': '用户明确延期'}
        s = state(decisions=[item], plan_requested=False)
        self.assertEqual('resolve_pending', controller.route(s)['action'])
        item['blocks_plan'] = False
        self.assertEqual('request_plan_transition', controller.route(s)['action'])

    def test_pause_wins_over_invalid_state(self):
        result = controller.route({'status': 'paused', 'wait_reason': '用户暂停'})
        self.assertEqual('paused', result['action'])
        self.assertTrue(result['errors'])
        p = subprocess.run([sys.executable, str(SCRIPT), 'next', '--json', json.dumps({'status':'paused'})], capture_output=True, text=True)
        self.assertEqual(0, p.returncode)
        self.assertEqual('paused', json.loads(p.stdout)['action'])

    def test_goal_stage_may_be_shown_with_plan_before_confirmation(self):
        s = state(phase='goals', plan={'presented':True,'evidence':'已发送计划'})
        self.assertEqual([],controller.validate(s))
        s['gates']['plan'] = '用户确认计划'
        self.assertEqual([],controller.validate(s))

    def test_entering_planning_after_a_request_to_skip_still_presents_both(self):
        s = state(phase='planning', plan_requested=True, plan_request_source='用户要求跳过计划并执行',
                  decisions=[], next_action='按主控展示计划和目标')
        result = controller.route(s)
        self.assertEqual('present_plan', result['action'])
        self.assertIn('一起展示正式计划和目标', result.get('instruction', controller.GUIDANCE['present_plan']))

    def test_explicit_skip_cannot_disable_plan_when_entering_planning(self):
        s = state(phase='planning', plan_requested=False, plan_required=False,
                  plan_waiver_source='用户要求跳过计划', decisions=[])
        self.assertIn('plan cannot be waived in planning stage', controller.validate(s))

    def test_old_plan_only_must_be_represented_with_goals(self):
        s = state(phase='planning', decisions=[], plan={'presented':True, 'evidence':'旧计划'},
                  next_action='展示目标')
        self.assertEqual('present_plan', controller.route(s)['action'])
        s['phase'] = 'discussion'
        self.assertEqual('present_plan', controller.route(s)['action'])
        s['decisions'] = [{'id':'d','subject':'目标范围','status':'pending'}]
        self.assertEqual('resolve_pending', controller.route(s)['action'])

    def test_execution_requires_both_actual_presentations(self):
        s = state(phase='execution', decisions=[], plan={'presented': True, 'evidence': '同一条正文'},
                  gates={'plan': '用户确认计划', 'goals': '用户确认目标', 'execution': '用户授权执行'})
        self.assertIn('goals must be presented before execution', controller.validate(s))
        s['goals'] = {'presented': True}
        self.assertIn('presented goals require evidence', controller.validate(s))
        s['goals'].update(evidence='同一条正文', presentation_id='计划展示')
        s['plan']['presentation_id'] = '计划展示'
        self.assertEqual([], controller.validate(s))
        s.update(plan_required=False, plan_requested=False, plan_waiver_source='免展示计划', plan={'presented': False})
        self.assertIn('plan must be presented before execution', controller.validate(s))

    def test_goals_cannot_be_shown_without_the_plan(self):
        s = state(phase='goals', plan_required=False, plan_requested=False,
                  plan_waiver_source='用户本轮只看目标', decisions=[])
        self.assertIn('plan must be presented before goals or execution', controller.validate(s))
        s['goals'] = {'presented': True, 'evidence': '已展示目标'}
        self.assertIn('goals cannot be presented without plan', controller.validate(s))
        s.update(phase='execution', goals={'presented':True,'evidence':'已展示目标','presentation_id':'目标展示'},
                 gates={'plan':'用户确认计划','goals':'用户确认目标','execution':'用户授权执行','subagents':'用户选择不开启'})
        self.assertIn('plan must be presented before execution', controller.validate(s))
        s.update(plan_required=True, plan={'presented':True,'evidence':'后续展示计划','presentation_id':'目标展示'})
        self.assertEqual([], controller.validate(s))

    def test_plan_and_goals_require_shared_presentation_id(self):
        s = state(
            decisions=[],
            plan={'presented': True, 'evidence': '同一条正文'},
            goals={'presented': True, 'evidence': '同一条正文'},
        )
        self.assertEqual([], controller.validate(s))
        s['goals']['presentation_id'] = '另一轮'
        self.assertIn('plan and goals require shared presentation_id', controller.validate(s))
        previous = state(
            decisions=[],
            plan={'presented': True, 'evidence': '第一轮计划', 'presentation_id': '第一轮'},
            goals={'presented': False},
        )
        current = copy.deepcopy(previous)
        current['goals'] = {
            'presented': True,
            'evidence': '第二轮目标',
            'presentation_id': '第二轮',
        }
        self.assertIn(
            'plan and goals must be presented with a shared presentation_id',
            controller.validate_transition(previous, current),
        )

    def test_execution_cannot_bypass_unchecked_coverage_or_pending_decisions(self):
        s = state(phase='execution', plan={'presented':True,'evidence':'已展示计划'},
                  goals={'presented':True,'evidence':'已展示目标'}, coverage_checked=False,
                  gates={'plan':'用户确认','goals':'用户确认','execution':'用户授权'})
        errors = controller.validate(s)
        self.assertIn('discussion coverage must be checked before execution', errors)
        self.assertIn('pending decisions prevent execution', errors)
        s['coverage_checked'] = True
        s['decisions'] = []
        self.assertEqual([], controller.validate(s))

    def test_unknown_operation_is_checked_even_when_a_decision_is_pending(self):
        operation = {'id':'op','reference':'原操作','status':'unknown','side_effect':True,'blocks_next':True}
        s = state(phase='execution', plan={'presented':True,'evidence':'已展示计划'},
                  goals={'presented':True,'evidence':'已展示目标'}, operations=[operation],
                  gates={'plan':'确认计划','goals':'确认目标','execution':'执行授权'})
        self.assertEqual('check_operation', controller.route(s)['action'])
        operation.update(status='succeeded', evidence='原操作回执')
        self.assertIn('pending decisions prevent execution', controller.validate(s))

    def test_revoked_execution_allows_only_observation_of_the_original_operation(self):
        op = {'id':'job', 'reference':'原作业', 'status':'unknown', 'side_effect':True, 'blocks_next':True}
        previous = state(phase='execution', decisions=[], plan={'presented':True,'evidence':'计划'},
                         goals={'presented':True,'evidence':'目标'}, operations=[op],
                         gates={'plan':'计划确认','goals':'目标确认','execution':'原执行授权'})
        current = copy.deepcopy(previous)
        current['gates']['execution'] = None
        current['next_action'] = '只读核实原作业'
        result = subprocess.run([sys.executable, str(SCRIPT), 'next', '--state', '-'],
                                input=json.dumps({'previous':previous, 'state':current}),
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertEqual('check_operation', json.loads(result.stdout)['action'])
        op = current['operations'][0]
        for status in ('unknown', 'running'):
            op['status'] = status
            self.assertEqual('check_operation', controller.route(current)['action'])
        for status in ('failed', 'succeeded'):
            op.update(status=status, evidence='原作业结果')
            current['next_action'] = '重试或继续下一步'
            self.assertEqual('repair_state', controller.route(current)['action'])
        op.update(status='unknown', blocks_next=False)
        self.assertEqual('repair_state', controller.route(current)['action'])

    def test_operation_observation_keeps_structure_pause_and_completion_guards(self):
        s = state(phase='execution', decisions=[], plan={'presented':True,'evidence':'计划'},
                  goals={'presented':True,'evidence':'目标'},
                  gates={'plan':'计划确认','goals':'目标确认','execution':None},
                  operations=[{'id':'job','reference':'原作业','status':'unknown','side_effect':True,'blocks_next':True}])
        s['operations'][0]['reference'] = ''
        self.assertEqual('repair_state', controller.route(s)['action'])
        s['operations'][0]['reference'] = '原作业'
        s['gates']['plan'] = None
        self.assertEqual('repair_state', controller.route(s)['action'])
        s['gates']['plan'] = '计划确认'
        s.update(status='paused', wait_reason='用户暂停')
        self.assertEqual('paused', controller.route(s)['action'])
        s.update(status='complete', completion_evidence='声称完成')
        self.assertEqual('repair_state', controller.route(s)['action'])
        s.update(status='continue', local_only=True, local_done=True)
        self.assertEqual('repair_state', controller.route(s)['action'])

    def test_waiting_preserves_independent_observation_after_execution_is_revoked(self):
        for waiting in ('wait_user', 'wait_tool'):
            for operation_status in ('unknown', 'running'):
                with self.subTest(waiting=waiting, operation_status=operation_status):
                    s = state(phase='execution', status=waiting, decisions=[],
                              wait_reason='等待后续条件', wait_evidence='已展示的问题',
                              plan={'presented':True,'evidence':'计划'}, goals={'presented':True,'evidence':'目标'},
                              gates={'plan':'计划确认','goals':'目标确认','execution':None},
                              operations=[{'id':'job','reference':'原作业','status':operation_status,
                                           'side_effect':True,'blocks_next':True,'independent_of_wait':True}])
                    result = controller.route(s)
                    self.assertEqual(waiting, result['action'])
                    self.assertEqual(['原作业'], result['independent_checks'])
                    self.assertIsNone(s['gates']['execution'])
                    s['independent_action'] = '继续实施其他修改'
                    result = controller.route(s)
                    self.assertEqual(waiting, result['action'])
                    self.assertEqual(['原作业'], result['independent_checks'])
                    self.assertNotIn('independent_action', result)
                    s.pop('independent_action')
                    s['operations'][0]['independent_of_wait'] = False
                    self.assertEqual('repair_state', controller.route(s)['action'])

    def test_plan_exception_requires_evidence(self):
        s = state(phase='analysis', plan_required=False, plan_requested=False)
        self.assertIn('plan waiver requires source', controller.validate(s))
        s['plan_waiver_source'] = '现有结果已经满足用户目标的证据'
        self.assertEqual([], controller.validate(s))
        s['phase'] = 'verification'
        self.assertIn('execution_occurred must be explicitly true or false', controller.validate(s))
        s['execution_occurred'] = False
        self.assertEqual([], controller.validate(s))
        s['execution_occurred'] = True
        self.assertIn('execution evidence required for execution or later', controller.validate(s))

    def test_waiver_does_not_authorize_an_unconfirmed_plan(self):
        s = state(phase='execution', plan_required=False, plan_requested=False, plan_waiver_source='用户允许免展示',
                  gates={'plan': None, 'goals': '用户确认目标', 'execution': '用户授权执行'})
        self.assertIn('plan evidence required for execution or later', controller.validate(s))

    def test_document_reference_alone_is_not_plan_presentation(self):
        s = state(phase='execution', decisions=[],
                  plan={'presented': False, 'evidence': '用户要求按设计文档执行'},
                  gates={'plan': '消息#3', 'goals': '消息#4', 'execution': '消息#5'})
        self.assertIn('plan must be presented before goals or execution', controller.validate(s))

    def test_presented_plan_still_needs_goal_evidence(self):
        s = state(phase='execution', decisions=[],
                  plan={'presented': True, 'evidence': '对话中已展示派生计划摘要'},
                  gates={'plan': '消息#4 用户确认计划', 'goals': None, 'execution': '消息#5'})
        self.assertIn('goals evidence required for execution or later', controller.validate(s))

    def test_plan_request_requires_a_traceable_source(self):
        s = state(decisions=[])
        del s['plan_request_source']
        self.assertIn('active plan request requires source', controller.validate(s))

    def test_active_plan_request_cannot_be_waived(self):
        s = state(plan_required=False, plan_waiver_source='先前允许免计划', plan_requested=True)
        self.assertIn('active plan request conflicts with waiver', controller.validate(s))

    def test_verify_existing_result_does_not_require_execution_authorization(self):
        s = state(phase='verification', plan={'presented':True,'evidence':'已发送计划'}, execution_occurred=False)
        self.assertEqual([], controller.validate(s))
        del s['execution_occurred']
        self.assertIn('execution_occurred must be explicitly true or false', controller.validate(s))

    def test_current_request_draft_and_local_scope(self):
        s = state(coverage_checked=False)
        self.assertEqual('present_incomplete_plan', controller.route(s)['action'])
        s['plan'].update(draft_presented=True, draft_evidence='上一轮已发送草案', draft_for_request=s['plan_request_source'])
        self.assertEqual('check_coverage', controller.route(s)['action'])
        s.update(local_only=True, local_done=False)
        self.assertEqual('continue_local', controller.route(s)['action'])
        s['local_done'] = True
        self.assertEqual('check_coverage', controller.route(s)['action'])
        s['coverage_checked'] = True
        self.assertEqual('local_complete', controller.route(s)['action'])

    def test_wait_does_not_hide_independent_work(self):
        s = state(status='wait_user', wait_reason='等待回答', wait_evidence='已发出问题', independent_action='检查已有资料')
        self.assertEqual('检查已有资料', controller.route(s)['independent_action'])

    def test_execution_block_does_not_block_authorized_goal_display(self):
        s = state(phase='planning', status='blocked', wait_reason='执行权限不足',
                  plan={'presented':True, 'evidence':'已展示计划'},
                  gates={'plan':'用户确认计划','goals':None,'execution':None},
                  independent_action='一起展示计划和目标')
        result = controller.route(s)
        self.assertEqual(('continue_local', '一起展示计划和目标', '执行权限不足'),
                         (result['action'], result['next_action'], result['blocked_reason']))
        self.assertEqual('blocked', s['status'])
        s.pop('independent_action')
        result = controller.route(s)
        self.assertEqual('continue_local', result['action'])
        self.assertIn('允许时一起展示计划和目标', result['next_action'])
        s['local_only'] = True
        self.assertEqual('blocked', controller.route(s)['action'])

    def test_blocked_state_does_not_suggest_missing_goal_if_plan_is_absent_or_goal_displayed(self):
        s = state(phase='planning', status='blocked', wait_reason='执行受阻', decisions=[])
        self.assertEqual('blocked', controller.route(s)['action'])
        s.update(plan={'presented':True,'evidence':'已展示计划','presentation_id':'同轮展示'},
                 goals={'presented':True,'evidence':'已展示目标','presentation_id':'同轮展示'})
        self.assertEqual('blocked', controller.route(s)['action'])

    def test_blocked_temporary_request_waits_even_if_main_has_independent_action(self):
        s = state(status='blocked', wait_reason='原任务受阻', independent_action='展示目标',
                  interruptions=[interruption(status='blocked', wait_reason='临时权限待处理')])
        result = controller.route(s)
        self.assertEqual(('wait_interruption', 'blocked'), (result['action'], result['status']))

    def test_interruption_runs_before_original_wait_and_preserves_state(self):
        s = state(status='wait_user', wait_reason='原问题未答', wait_evidence='原问题已展示',
                  next_action='等待原问题', local_only=True, local_done=False, interruptions=[interruption()])
        original = copy.deepcopy(s)
        result = controller.route(s)
        self.assertEqual('handle_interruption', result['action'])
        self.assertEqual('查询官网', result['next_action'])
        self.assertEqual('wait_user', result['resume_point']['status'])
        self.assertEqual(original, s)

    def test_completed_interruption_requires_reconciliation_before_resuming(self):
        original = state(status='wait_user', wait_reason='原问题未答', wait_evidence='原问题已展示',
                         next_action='等待原问题', interruptions=[interruption()])
        self.assertIn('cannot resume before interruption completes or is cancelled',
                      controller.validate_transition(original, dict(original, interruptions=[])))
        completed = copy.deepcopy(original)
        completed['interruptions'][0].update(status='complete', result_evidence='官网结果已交付',
                                             resume_point=controller.route(original)['resume_point'])
        result = controller.route(completed)
        self.assertEqual(('reconcile_interruption', 'task-a'), (result['action'], result['resume_to']))
        resumed = dict(completed, interruptions=[])
        self.assertEqual([], controller.validate_transition(completed, resumed))
        self.assertEqual('wait_user', controller.route(resumed)['action'])

    def test_new_evidence_can_make_original_fact_question_unnecessary(self):
        completed = state(status='wait_user', wait_reason='等待事实', wait_evidence='原问题已展示',
                          plan_requested=False, interruptions=[interruption()])
        completed['interruptions'][0].update(status='complete', result_evidence='官网证据已交付',
                                             resume_point=controller.route(completed)['resume_point'])
        resumed = copy.deepcopy(completed)
        resumed.update(status='continue', next_action='确认是否结束讨论', interruptions=[],
                       interruption_resumed_id='temp-1', interruption_resume_source='已核对官网事实')
        resumed['decisions'][0].update(status='excluded', source='官网证据使该事实问题不再需要用户回答')
        self.assertEqual([], controller.validate_transition(completed, resumed))
        self.assertEqual('request_plan_transition', controller.route(resumed)['action'])

    def test_interruption_waits_for_its_own_answer_and_cannot_fake_completion(self):
        s = state(interruptions=[interruption(status='wait_user', wait_reason='等待临时问题')])
        self.assertEqual('repair_state', controller.route(s)['action'])
        s['interruptions'][0]['wait_evidence'] = '临时问题已展示'
        self.assertEqual('wait_interruption', controller.route(s)['action'])
        s['interruptions'][0].update(status='complete')
        self.assertEqual('repair_state', controller.route(s)['action'])

    def test_original_pause_stays_after_an_explicit_temporary_request(self):
        s = state(status='paused', wait_reason='用户暂停原任务', interruptions=[interruption()])
        self.assertEqual('paused', controller.route(s)['action'])
        s['interruptions'][0]['allow_while_paused'] = True
        self.assertEqual('paused', controller.route(s)['action'])
        self.assertIn('interruption while paused requires explicit request source', controller.route(s)['errors'])
        s['interruptions'][0]['allow_while_paused_source'] = '用户另行要求查官网'
        self.assertEqual('handle_interruption', controller.route(s)['action'])
        s['interruptions'][0].update(status='complete', result_evidence='临时结果已交付',
                                     resume_point=controller.route(s)['resume_point'])
        self.assertEqual('reconcile_interruption', controller.route(s)['action'])
        resumed = dict(s, interruptions=[], interruption_resumed_id='temp-1',
                       interruption_resume_source='核对后继续保持用户暂停')
        self.assertEqual([], controller.validate_transition(s, resumed))
        self.assertEqual('paused', controller.route(resumed)['action'])

    def test_nested_interruption_resumes_one_level_at_a_time(self):
        first = interruption(id='first')
        second = interruption(id='second', request='临时插问', source='用户后续消息')
        s = state(interruptions=[first, second])
        self.assertEqual('second', controller.route(s)['interruption_id'])
        s['interruptions'][1].update(status='complete', result_evidence='插问已回答',
                                     resume_point=controller.route(s)['resume_point'])
        self.assertEqual('first', controller.route(s)['resume_to'])
        self.assertIn('resume one interruption at a time',
                      controller.validate_transition(s, dict(s, interruptions=[])))

    def test_interruption_can_be_handled_without_hiding_invalid_original_state(self):
        s = state(phase='execution', interruptions=[interruption()])
        result = controller.route(s)
        self.assertEqual('handle_interruption', result['action'])
        self.assertIn('goals must be presented before execution', result['original_state_errors'])
        s['interruptions'][0].update(status='complete', result_evidence='证据已交付',
                                     resume_point=result['resume_point'])
        resumed = dict(s, interruptions=[], interruption_resumed_id='temp-1',
                       interruption_resume_source='核对原执行状态')
        self.assertEqual('repair_state', controller.route(resumed)['action'])

    def test_pause_is_preserved_and_transition_errors_remain_visible(self):
        previous = state(status='paused', wait_reason='用户暂停', interruptions=[interruption()])
        current = dict(previous, interruptions=[])
        payload = {'previous':previous, 'state':current}
        p = subprocess.run([sys.executable, str(SCRIPT), 'next', '--json', json.dumps(payload)],
                           capture_output=True, text=True, check=True)
        result = json.loads(p.stdout)
        self.assertEqual('paused', result['action'])
        self.assertIn('cannot resume before interruption completes or is cancelled', result['errors'])

    def test_cancelled_interruption_is_not_mistaken_for_success(self):
        s = state(interruptions=[interruption()])
        s['interruptions'][0].update(status='cancelled', result_evidence='用户取消该请求',
                                     resume_point=controller.route(s)['resume_point'])
        result = controller.route(s)
        self.assertEqual(('reconcile_interruption', 'cancelled'), (result['action'], result['outcome']))
        changed = copy.deepcopy(s)
        changed['interruptions'][0]['status'] = 'complete'
        self.assertIn('completed interruption cannot change status', controller.validate_transition(s, changed))

    def test_paused_interruption_requires_explicit_resume(self):
        previous = state(interruptions=[interruption(status='paused', wait_reason='用户暂停临时请求')])
        current = copy.deepcopy(previous)
        current['interruptions'][0]['status'] = 'continue'
        self.assertIn('resuming paused interruption requires source', controller.validate_transition(previous, current))
        current['interruptions'][0]['resume_source'] = '用户要求继续临时请求'
        self.assertEqual([], controller.validate_transition(previous, current))

    def test_blocked_interruption_can_be_cancelled_or_continued_without_keywords(self):
        s = state(status='wait_user', wait_reason='原问题未答', wait_evidence='原问题已展示',
                  interruptions=[interruption()])
        point = controller.route(s)['resume_point']
        frame = s['interruptions'][0]
        frame.update(status='blocked', wait_reason='等待权限', resume_point=point)
        self.assertEqual('wait_interruption', controller.route(s)['action'])
        cancelled = copy.deepcopy(s)
        cancelled['interruptions'][0].update(status='cancelled', result_evidence='用户明确取消临时请求')
        result = controller.route(cancelled)
        self.assertEqual(('reconcile_interruption', 'cancelled', 'wait_user'),
                         (result['action'], result['outcome'], result['resume_point']['status']))
        frame['status'] = 'continue'
        self.assertEqual('handle_interruption', controller.route(s)['action'])

    def test_completed_interruption_without_saved_resume_point_must_be_recovered(self):
        s = state(interruptions=[interruption(status='complete', result_evidence='文件已读取')])
        result = controller.route(s)
        self.assertEqual('repair_state', result['action'])
        self.assertIn('interruption resume_point required before reconciliation', result['errors'])

    def test_interruption_cli_lifecycle_reconciles_before_original_wait(self):
        parent = state(status='wait_user', wait_reason='原问题未答', wait_evidence='原问题已展示',
                       next_action='等待原问题')
        active = dict(parent, interruptions=[interruption()])
        completed = copy.deepcopy(active)
        completed['interruptions'][0].update(status='complete', result_evidence='网站结果已交付',
                                             resume_point=controller.route(active)['resume_point'])
        resumed = dict(completed, interruptions=[], interruption_resumed_id='temp-1',
                       interruption_resume_source='已核对原问题仍未回答')
        for previous, current, expected in ((parent, active, 'handle_interruption'),
                                            (active, completed, 'reconcile_interruption'),
                                            (completed, resumed, 'wait_user')):
            payload = {'previous':previous, 'state':current}
            p = subprocess.run([sys.executable, str(SCRIPT), 'next', '--json', json.dumps(payload)],
                               capture_output=True, text=True, check=True)
            self.assertEqual(expected, json.loads(p.stdout)['action'])

    def test_single_state_carries_resume_point_without_full_previous_snapshot(self):
        s = state(status='wait_user', wait_reason='原问题未答', wait_evidence='原问题已展示',
                  next_action='等待原问题', interruptions=[interruption()])
        point = controller.route(s)['resume_point']
        s['interruptions'][0].update(status='complete', result_evidence='结果已取得', resume_point=point)
        p = subprocess.run([sys.executable, str(SCRIPT), 'next', '--json', json.dumps(s)],
                           capture_output=True, text=True, check=True)
        result = json.loads(p.stdout)
        self.assertEqual('reconcile_interruption', result['action'])
        self.assertEqual(point, result['resume_point'])
        self.assertEqual('structure_only', result['scope'])

    def test_saved_resume_point_survives_later_root_state_changes(self):
        s = state(status='wait_user', wait_reason='原问题未答', wait_evidence='原问题已展示',
                  next_action='等待原问题', interruptions=[interruption()])
        point = controller.route(s)['resume_point']
        s.update(status='continue', next_action='处理临时事项')
        s['interruptions'][0].update(status='complete', result_evidence='结果已取得', resume_point=point)
        result = controller.route(s)
        self.assertEqual('wait_user', result['resume_point']['status'])
        self.assertEqual('等待原问题', result['resume_point']['next_action'])

    def test_saved_resume_point_cannot_be_rewritten_when_prior_state_is_available(self):
        previous = state(status='wait_user', wait_reason='原问题未答', wait_evidence='原问题已展示',
                         next_action='等待原问题', interruptions=[interruption()])
        previous['interruptions'][0]['resume_point'] = controller.route(previous)['resume_point']
        current = copy.deepcopy(previous)
        current['interruptions'][0]['resume_point']['status'] = 'continue'
        self.assertIn('saved interruption resume_point cannot change', controller.validate_transition(previous, current))

    def test_resume_point_with_no_identifiable_parent_is_rejected(self):
        s = state(interruptions=[interruption(status='complete', result_evidence='结果',
                                             resume_point={'status':'continue','next_action':'继续'})])
        self.assertIn('resume_point requires original phase or interruption id', controller.validate(s))

    def test_temporary_request_can_report_parent_errors_without_declaring_check_passed(self):
        s = state(phase='execution', interruptions=[interruption()])
        p = subprocess.run([sys.executable, str(SCRIPT), 'next', '--json', json.dumps(s)],
                           capture_output=True, text=True, check=True)
        result = json.loads(p.stdout)
        self.assertEqual('handle_interruption', result['action'])
        self.assertTrue(result['original_state_errors'])
        check = subprocess.run([sys.executable, str(SCRIPT), 'check', '--json', json.dumps(s)],
                               capture_output=True, text=True)
        self.assertNotEqual(0, check.returncode)
        self.assertFalse(json.loads(check.stdout)['ok'])

    def test_draft_cannot_be_marked_presented_without_delivery_reference(self):
        s = state(plan={'presented': False, 'draft_presented': True})
        self.assertIn('presented draft requires evidence', controller.validate(s))
        self.assertEqual('repair_state', controller.route(s)['action'])

    def test_presented_plan_is_not_reissued_as_draft_on_confirmation(self):
        s = state(plan={'presented': True, 'evidence': '上一轮正式计划正文'},
                  decisions=[{'id':'confirmation','subject':'计划确认','status':'pending'}])
        self.assertEqual('resolve_pending', controller.route(s)['action'])
        s['coverage_checked'] = False
        self.assertEqual('check_coverage', controller.route(s)['action'])

    def test_plan_requires_real_presentation_evidence(self):
        s = state(phase='goals')
        self.assertIn('plan must be presented before goals or execution', controller.validate(s))
        s['plan'] = {'presented': True}
        self.assertIn('presented plan requires evidence', controller.validate(s))

    def test_decision_needs_actual_value_not_only_topic_and_source(self):
        s = state(decisions=[{'id':'refund','subject':'退款规则','status':'decided','source':'用户第 2 轮'}])
        self.assertIn('decided item requires its actual value', controller.validate(s))
        s['decisions'][0]['value'] = '退款金额不得超过实付金额'
        self.assertEqual([], controller.validate(s))

    def test_reported_old_draft_does_not_block_confirmed_formal_plan(self):
        s = state(decisions=[], phase='goals', plan={'presented':True,'evidence':'上轮正式计划',
                  'presentation_id':'上轮正式计划',
                  'draft_delivery':{'status':'reported','evidence':'旧草案'}},
                  gates={'plan':'用户确认计划','goals':None,'execution':None})
        self.assertEqual('present_plan', controller.route(s)['action'])
        s['goals'] = {'presented':True, 'evidence':'合并展示目标', 'presentation_id':'上轮正式计划'}
        self.assertEqual('continue_current_phase', controller.route(s)['action'])

    def test_new_plan_request_is_not_satisfied_by_old_draft(self):
        s=state(plan_request_source='本轮请求',plan={'presented':False,'draft_presented':True,
                'draft_evidence':'上一轮草案','draft_for_request':'旧请求'})
        self.assertEqual('verify_plan_request',controller.route(s)['action'])
        s['plan']['draft_not_for_request']='本轮请求'
        self.assertEqual('present_incomplete_plan',controller.route(s)['action'])
        s['plan'].pop('draft_not_for_request')
        s['plan']['draft_for_request']='本轮请求'
        self.assertEqual('resolve_pending',controller.route(s)['action'])
        s['plan'].pop('draft_for_request')
        self.assertEqual('verify_plan_request',controller.route(s)['action'])
        s['decisions']=[]
        self.assertEqual('present_plan',controller.route(s)['action'])

    def test_old_draft_can_be_distinguished_without_old_request_reference(self):
        s=state(plan_request_source='本轮请求',plan={'presented':False,'draft_presented':True,
                'draft_evidence':'旧草案先于本轮请求','draft_not_for_request':'本轮请求'})
        self.assertEqual('present_incomplete_plan',controller.route(s)['action'])
        s['plan']['draft_for_request']='本轮请求'
        self.assertIn('draft request references conflict',controller.validate(s))
        self.assertEqual('repair_state',controller.route(s)['action'])

    def test_new_request_draft_lifecycle_does_not_repeat(self):
        s=state(plan_request_source='本轮请求',plan={'presented':False,'draft_presented':True,
                'draft_evidence':'旧草案','draft_not_for_request':'本轮请求'})
        self.assertEqual('present_incomplete_plan',controller.route(s)['action'])
        s['plan'].update(draft_evidence='本轮已交付草案',draft_for_request='本轮请求')
        s['plan'].pop('draft_not_for_request')
        self.assertEqual('resolve_pending',controller.route(s)['action'])

    def test_draft_request_reference_requires_a_delivered_draft(self):
        s=state(plan={'presented':False,'draft_for_request':'某条请求'})
        self.assertIn('draft_for_request requires presented draft',controller.validate(s))
        s['plan']['draft_for_request']=''
        self.assertIn('draft_for_request must be a nonempty reference',controller.validate(s))

    def test_reported_draft_does_not_block_new_formal_plan(self):
        s = state(decisions=[], plan={'presented':False,'draft_presented':True,
                  'draft_evidence':'上轮草案','draft_delivery':{'status':'reported','evidence':'旧草案'}})
        self.assertEqual('present_plan', controller.route(s)['action'])

    def test_direct_cli_does_not_create_bytecode(self):
        with tempfile.TemporaryDirectory() as d:
            import shutil
            copied=Path(d)/'workflow_control.py';shutil.copy2(SCRIPT,copied)
            p=subprocess.run([sys.executable,str(copied),'next','--json',json.dumps(state(decisions=[]))],capture_output=True,text=True,check=True)
            self.assertEqual('present_plan',json.loads(p.stdout)['action'])
            self.assertFalse((Path(d)/'__pycache__').exists())

    def test_never_treat_missing_source_as_confirmation(self):
        s = state(decisions=[{'id': '1', 'subject': '范围', 'status': 'decided'}])
        self.assertIn('resolved decision requires source', controller.validate(s))

    def test_cannot_complete_before_required_plan_is_presented(self):
        for phase in ('discussion', 'planning'):
            s = state(phase=phase, status='complete', decisions=[], completion_evidence='其他结果')
            self.assertIn('required plan must be presented before completion', controller.validate(s))
            self.assertEqual('repair_state', controller.route(s)['action'])

        s = state(phase='planning', status='complete', decisions=[], completion_evidence='计划已交付',
                  plan={'presented':True, 'evidence':'计划正文', 'presentation_id':'计划正文'})
        self.assertIn('required goals must be presented before completion', controller.validate(s))
        self.assertEqual('repair_state', controller.route(s)['action'])
        s['goals'] = {'presented':True, 'evidence':'计划与目标正文', 'presentation_id':'计划正文'}
        self.assertEqual('complete', controller.route(s)['action'])

    def test_cannot_complete_before_coverage_check(self):
        s = state(status='complete', decisions=[], coverage_checked=False,
                  plan={'presented':True, 'evidence':'正式计划已发出'}, completion_evidence='正文')
        self.assertIn('coverage check required before completion', controller.validate(s))

    def test_complete_requires_no_pending_and_evidence(self):
        errors = controller.validate(state(status='complete'))
        self.assertIn('pending decisions prevent completion', errors)
        self.assertIn('completion evidence required', errors)

    def test_malformed_types_do_not_crash(self):
        for field in ('phase', 'status'):
            s = state(**{field: []})
            self.assertTrue(controller.validate(s))

    def test_unknown_side_effect_prevents_completion_but_pause_is_respected(self):
        op={'id':'job','reference':'原操作','status':'unknown','side_effect':True,'blocks_next':True}
        s=state(plan={'presented':True,'evidence':'之前已展示'}, decisions=[], operations=[op])
        self.assertEqual('check_operation', controller.route(s)['action'])
        s.update(status='complete',completion_evidence='正文已交付')
        self.assertIn('unresolved operation prevents completion',controller.validate(s))
        s.update(status='paused',wait_reason='用户暂停')
        self.assertEqual('paused',controller.route(s)['action'])

    def test_blocking_read_only_operation_must_be_observed_before_next_or_completion(self):
        op = {'id':'search', 'reference':'原调查', 'status':'running', 'side_effect':False, 'blocks_next':True}
        s = state(phase='execution', decisions=[], plan={'presented':True,'evidence':'计划正文'},
                  goals={'presented':True,'evidence':'目标正文'},
                  gates={'plan':'确认计划','goals':'确认目标','execution':'执行授权'}, operations=[op])
        self.assertEqual('check_operation', controller.route(s)['action'])
        op['status'] = 'unknown'
        self.assertEqual('check_operation', controller.route(s)['action'])
        s.update(status='complete', completion_evidence='已交付')
        self.assertIn('unresolved operation prevents completion', controller.validate(s))
        op.update(status='succeeded', evidence='实际结果')
        self.assertNotIn('unresolved operation prevents completion', controller.validate(s))

    def test_read_only_operation_can_be_checked_independently_while_waiting(self):
        op = {'id':'search', 'reference':'原调查', 'status':'running', 'side_effect':False,
              'blocks_next':False, 'independent_of_wait':True}
        s = state(status='wait_user', wait_reason='等待决定', wait_evidence='已展示问题', operations=[op])
        self.assertEqual(['原调查'], controller.route(s)['independent_checks'])

    def test_operation_fields_and_result_evidence_are_validated(self):
        op={'id':'job','reference':'原操作','status':'unkown','side_effect':True,'blocks_next':True}
        s=state(decisions=[],plan={'presented':True,'evidence':'已展示'},status='complete',completion_evidence='已交付',operations=[op])
        self.assertIn('invalid operation status',controller.validate(s))
        op['status']='succeeded'
        self.assertIn('operation result requires evidence',controller.validate(s))
        op.update(status='unknown',blocks_completion=False)
        self.assertIn('nonblocking operation requires reason',controller.validate(s))
        op['blocks_next']='false'
        self.assertIn('operation blocks_next must be boolean',controller.validate(s))

    def test_local_work_checks_blocking_unknown_side_effect_before_retry(self):
        op={'id':'a','reference':'原操作','status':'unknown','side_effect':True,'blocks_next':True}
        s=state(phase='execution', decisions=[], plan={'presented':True,'evidence':'已展示计划'},
                goals={'presented':True,'evidence':'已展示目标'},
                gates={'plan':'确认','goals':'确认','execution':'授权'},local_only=True,local_done=False,
                next_action='重试原操作',operations=[op])
        self.assertEqual('check_operation',controller.route(s)['action'])
        op['blocks_next']=False
        self.assertEqual('continue_local',controller.route(s)['action'])
        op['blocks_next']=True;s['local_done']=True
        self.assertEqual('check_operation',controller.route(s)['action'])
        op.update(status='running')
        self.assertEqual('check_operation',controller.route(s)['action'])
        op.update(status='succeeded',evidence='命令已完成')
        self.assertEqual('local_complete',controller.route(s)['action'])
        op.update(status='failed',evidence='命令失败')
        self.assertEqual('handle_operation_failure',controller.route(s)['action'])
        s.update(status='paused',wait_reason='用户暂停')
        self.assertEqual('paused',controller.route(s)['action'])

    def test_final_rejects_failed_blocking_operation(self):
        op={'id':'a','reference':'原操作','status':'failed','side_effect':True,
            'blocks_next':True,'evidence':'命令失败'}
        s=state(status='wait_user',wait_reason='等待用户',wait_evidence='已展示问题',
                plan_requested=False,local_only=True,local_done=True,
                discussion_question_waiver_source='用户要求本轮只解释',
                operations=[op])
        self.assertIn(
            'discussion final blocked by unresolved operation: 原操作',
            controller.validate_discussion_final(s,'解释完成。',handoff('waived')),
        )

    def test_failed_blocking_operation_prevents_overall_completion(self):
        op = {'id': 'a', 'reference': '原操作', 'status': 'failed', 'side_effect': True,
              'blocks_next': False, 'evidence': '命令失败'}
        s = state(
            phase='execution', status='complete', decisions=[],
            plan={'presented': True, 'evidence': '计划'},
            goals={'presented': True, 'evidence': '目标'},
            gates={'plan': '确认', 'goals': '确认', 'execution': '授权',
                   'subagents': '用户委托'},
            completion_evidence='已交付', operations=[op],
        )
        self.assertIn('unresolved operation prevents completion', controller.validate(s))

    def test_failed_blocking_operation_precedes_waiting_status(self):
        op = {'id': 'a', 'reference': '原操作', 'status': 'failed',
              'side_effect': True, 'blocks_next': True, 'evidence': '命令失败'}
        for status in ('wait_user', 'wait_tool'):
            s = state(
                status=status, wait_reason='等待外部条件',
                wait_evidence='已展示问题', plan_requested=False,
                decisions=[], operations=[op],
            )
            self.assertEqual('handle_operation_failure', controller.route(s)['action'])

    def test_superseded_goal_cannot_be_used_for_completion(self):
        s = state(
            phase='execution', status='complete', decisions=[],
            plan={'presented': True, 'evidence': '计划'},
            goals={
                'presented': True,
                'evidence': '旧目标',
                'status': 'superseded',
                'source': '用户新范围',
                'superseded_by': '新目标',
            },
            gates={'plan': '确认', 'goals': '旧目标确认', 'execution': '授权',
                   'subagents': '用户选择不开启'},
            completion_evidence='已交付',
        )
        self.assertIn('superseded goals cannot be used for completion', controller.validate(s))

    def test_business_completion_can_report_stale_host_goal(self):
        s = state(
            phase='execution', status='complete', decisions=[],
            plan={'presented': True, 'evidence': '新范围计划'},
            goals={'presented': True, 'evidence': '新范围目标', 'status': 'active'},
            superseded_goals=[{
                'objective': '旧范围目标',
                'host_id': 'host-1',
                'source': '用户新范围',
                'superseded_by': '新范围目标',
            }],
            host_goal_sync='stale',
            gates={'plan': '确认', 'goals': '新目标确认', 'execution': '授权',
                   'subagents': '用户选择不开启'},
            completion_evidence='新范围已验收',
        )
        self.assertEqual([], controller.validate(s))

    def test_changed_goal_requires_current_confirmation_source(self):
        previous = state(
            goals={'presented': True, 'evidence': '旧目标'},
            gates={'plan': '旧计划确认', 'goals': '旧目标确认',
                   'execution': '旧执行授权', 'subagents': '用户选择不开启'},
            decisions=[], plan_requested=False,
        )
        current = copy.deepcopy(previous)
        current['goals']['evidence'] = '新目标'
        current['impact_review'] = {'reason': '范围变化', 'retained': ['plan']}
        current['superseded_goals'] = [{
            'objective': '旧目标',
            'host_id': 'host-1',
            'source': '用户新范围',
            'superseded_by': '新目标',
        }]
        self.assertIn(
            'changed goals require current goal confirmation source',
            controller.validate_transition(previous, current),
        )
        current['gates']['goals'] = None
        self.assertIn(
            'changed goals require current goal confirmation source',
            controller.validate_transition(previous, current),
        )
        previous['gates']['goals'] = None
        self.assertIn(
            'changed goals require current goal confirmation source',
            controller.validate_transition(previous, current),
        )

    def test_duplicate_operations_are_not_treated_as_new_work(self):
        op={'id':'a','reference':'同一个作业','status':'unknown','side_effect':True,'blocks_next':True}
        s=state(operations=[op,dict(op,id='b')])
        self.assertIn('operation reference missing or duplicated',controller.validate(s))

    def test_one_message_can_confirm_plan_goals_and_execution(self):
        s=state(phase='execution',decisions=[],plan={'presented':True,'evidence':'已展示计划'},
                goals={'presented':True,'evidence':'已展示目标'},
                gates={'plan':'用户第 3 条','goals':'用户第 3 条','execution':'用户第 3 条'})
        self.assertEqual([],controller.validate(s))

    def test_transition_does_not_silently_withdraw_plan_request(self):
        previous=state(decisions=[]);current=dict(previous,plan_requested=False)
        self.assertIn('withdrawing plan request requires source',controller.validate_transition(previous,current))
        current['plan_request_change_source']='用户明确撤回'
        self.assertEqual([],controller.validate_transition(previous,current))

    def test_fulfilled_plan_request_can_be_cleared(self):
        previous=state(decisions=[])
        current=dict(previous,plan_requested=False,plan={'presented':True,'evidence':'已列出计划'})
        self.assertEqual([],controller.validate_transition(previous,current))

    def test_old_plan_does_not_fulfil_new_plan_request(self):
        previous=state(decisions=[],plan={'presented':True,'evidence':'旧计划'})
        current=dict(previous,plan_requested=False)
        self.assertIn('withdrawing plan request requires source',controller.validate_transition(previous,current))
        current['plan']={'presented':True,'evidence':'新计划'}
        self.assertEqual([],controller.validate_transition(previous,current))

    def test_previously_delivered_request_can_be_cleared_with_delivery_reference(self):
        previous=state(decisions=[],plan={'presented':True,'evidence':'已交付本次请求的计划'})
        current=dict(previous,plan_requested=False,plan_request_delivery_source='本次请求的交付消息')
        self.assertEqual([],controller.validate_transition(previous,current))

    def test_malformed_impact_review_is_reported(self):
        old=state(decisions=[{'id':'x','subject':'范围','status':'decided','value':'只读','source':'旧'}],gates={'plan':'旧授权','goals':None,'execution':None})
        new=dict(old,decisions=[{'id':'x','subject':'范围','status':'decided','value':'写入','source':'新'}],impact_review={'reason':'已检查','retained':[{}]})
        self.assertIn('changed scope requires reviewing retained authorizations',controller.validate_transition(old,new))

    def test_transition_preserves_user_decision_source_and_pause(self):
        previous=state(status='paused',wait_reason='用户暂停',decisions=[{'id':'x','subject':'范围','status':'decided','value':'不删除','source':'用户旧要求'}])
        current=dict(previous,status='continue',decisions=[{'id':'x','subject':'范围','status':'decided','value':'允许删除','source':'用户旧要求'}])
        errors=controller.validate_transition(previous,current)
        self.assertIn('resuming paused task requires source',errors)
        self.assertIn('changed decision requires new source',errors)
        current['resume_source']='用户明确恢复';current['decisions'][0]['source']='用户明确修改'
        self.assertEqual([],controller.validate_transition(previous,current))

    def test_changed_decision_requires_review_of_unchanged_authorizations(self):
        old=state(phase='execution',plan={'presented':True,'evidence':'旧计划'},
                  decisions=[{'id':'scope','subject':'范围','status':'decided','value':'只读','source':'消息2'}],
                  gates={'plan':'消息2','goals':'消息2','execution':'消息2'})
        new=dict(old,decisions=[{'id':'scope','subject':'范围','status':'decided','value':'写入','source':'消息3'}],gates=dict(old['gates']))
        self.assertIn('changed scope requires reviewing retained authorizations',controller.validate_transition(old,new))
        new['impact_review']={'reason':'已有授权明确涵盖新范围','retained':['plan','goals','execution','subagents']}
        self.assertEqual([],controller.validate_transition(old,new))
        new.pop('impact_review');new['gates']={'plan':'消息3','goals':'消息3','execution':'消息3'}
        self.assertEqual([],controller.validate_transition(old,new))

    def test_excluded_and_delegated_changes_cannot_silently_reuse_old_authority(self):
        for status in ('excluded', 'delegated'):
            with self.subTest(status=status):
                old = state(decisions=[{'id':'d1','subject':'发布范围','status':status,
                                        'value':'不发布','source':'原要求'}],
                            gates={'plan':'原授权','goals':'原授权','execution':'原授权'})
                new = copy.deepcopy(old)
                new['decisions'][0].update(status='decided', value='发布')
                errors = controller.validate_transition(old, new)
                self.assertIn('changed decision requires new source', errors)
                self.assertIn('changed scope requires reviewing retained authorizations', errors)
                new['decisions'][0]['source'] = '用户新的明确要求'
                new['impact_review'] = {'reason':'核对新要求覆盖的范围', 'retained':list(controller.GATES)}
                self.assertEqual([], controller.validate_transition(old, new))
                removed = copy.deepcopy(old)
                removed['decisions'] = []
                errors = controller.validate_transition(old, removed)
                self.assertIn('removed decision requires source', errors)
                self.assertIn('changed scope requires reviewing retained authorizations', errors)
                removed['removed_decisions'] = {'d1':'用户明确撤回该事项'}
                removed['impact_review'] = {'reason':'撤回不影响其余授权', 'retained':list(controller.GATES)}
                self.assertEqual([], controller.validate_transition(old, removed))

    def test_delegated_adjustment_reuses_its_source_only_with_impact_review(self):
        old = state(decisions=[{'id':'d1','subject':'标题措辞','status':'delegated',
                                'value':'方案甲','source':'用户委托标题措辞'}],
                    gates={'plan':'委托方案','goals':'确认目标','execution':'执行授权'})
        new = copy.deepcopy(old)
        new['decisions'][0]['value'] = '方案乙'
        self.assertTrue(controller.validate_transition(old, new))
        new['impact_review'] = {'reason':'仍仅调整标题措辞，原委托及其余授权均适用',
                                'retained':list(controller.GATES)}
        self.assertEqual([], controller.validate_transition(old, new))
        new['decisions'][0]['subject'] = '标题和正文'
        self.assertIn('changed decision requires new source', controller.validate_transition(old, new))

    def test_removed_decision_and_new_plan_need_sources_and_impact_review(self):
        old=state(plan={'presented':True,'evidence':'旧计划'},
                  decisions=[{'id':'x','subject':'范围','status':'decided','value':'只读','source':'消息2'}],
                  gates={'plan':'消息2','goals':None,'execution':'消息2'})
        new=dict(old,decisions=[],plan={'presented':True,'evidence':'新计划'},gates=dict(old['gates']))
        errors=controller.validate_transition(old,new)
        self.assertIn('removed decision requires source',errors)
        self.assertIn('changed scope requires reviewing retained authorizations',errors)

    def test_transition_checks_old_plan_authority(self):
        previous=state(plan={'presented':True,'evidence':'旧计划'},gates={'plan':'旧确认','goals':'目标','execution':'旧执行授权'})
        current=dict(previous,plan={'presented':False},gates=dict(previous['gates']))
        errors=controller.validate_transition(previous,current)
        self.assertIn('changed plan requires reviewing old plan authorization',errors)
        self.assertIn('changed plan requires reviewing old execution authorization',errors)
        current['gates'].update(plan=None,execution=None)
        self.assertEqual([],controller.validate_transition(previous,current))

    def test_changed_goals_reopen_only_the_affected_authorizations(self):
        previous=state(goals={'presented':True,'evidence':'旧目标'},
                       gates={'plan':'计划确认','goals':'目标确认','execution':'执行授权'})
        current=dict(previous,goals={'presented':False},gates=dict(previous['gates']))
        errors=controller.validate_transition(previous,current)
        self.assertIn('changed goals require reviewing old goals authorization',errors)
        self.assertIn('changed goals require reviewing old execution authorization',errors)
        current['gates'].update(goals=None,execution=None)
        self.assertEqual([],controller.validate_transition(previous,current))

    def test_plan_delta_keeps_unaffected_goal_confirmation(self):
        previous = state(plan={'presented':True, 'evidence':'原计划正文'},
                         goals={'presented':True, 'evidence':'原目标正文'},
                         gates={'plan':'原计划确认','goals':'原目标确认','execution':'原执行授权'})
        current = copy.deepcopy(previous)
        current['plan']['evidence'] = '原计划正文及第2项修改'
        current['gates'].update(plan='第2项新确认', execution=None)
        current['impact_review'] = {'reason':'目标及子代理选择不受第2项修改影响', 'retained':['goals','subagents']}
        self.assertEqual([], controller.validate_transition(previous, current))
        self.assertEqual('原目标确认', current['gates']['goals'])

    def test_goal_delta_keeps_unaffected_plan_confirmation(self):
        previous = state(plan={'presented':True, 'evidence':'原计划正文'},
                         goals={'presented':True, 'evidence':'原目标正文'},
                         gates={'plan':'原计划确认','goals':'原目标确认','execution':'原执行授权'})
        current = copy.deepcopy(previous)
        current['goals']['evidence'] = '原目标正文及新增目标'
        current['gates'].update(goals='新增目标确认', execution=None)
        current['superseded_goals'] = [{
            'objective': '原目标正文',
            'host_id': 'host-old',
            'source': '用户新增目标',
            'superseded_by': '原目标正文及新增目标',
        }]
        current['impact_review'] = {'reason':'已确认计划及子代理选择不受新增目标影响', 'retained':['plan','subagents']}
        self.assertEqual([], controller.validate_transition(previous, current))
        self.assertEqual('原计划确认', current['gates']['plan'])

    def test_cli_supports_optional_transition_comparison(self):
        previous=state(decisions=[]);current=dict(previous,plan_requested=False)
        payload={'previous':previous,'state':current}
        p=subprocess.run([sys.executable,str(SCRIPT),'next','--json',json.dumps(payload)],capture_output=True,text=True)
        self.assertNotEqual(0,p.returncode)
        self.assertEqual('repair_state',json.loads(p.stdout)['action'])

    def test_cli_marks_validation_as_structural_only(self):
        p=subprocess.run([sys.executable,str(SCRIPT),'check','--json',json.dumps(state(decisions=[]))],capture_output=True,text=True,check=True)
        result=json.loads(p.stdout)
        self.assertTrue(result['ok']);self.assertEqual('structure_only',result['scope'])

    def test_state_file_metadata_is_untouched(self):
        import shutil
        if sys.platform != 'darwin' or not shutil.which('xattr'):
            self.skipTest('macOS extended attributes unavailable')
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'state.json';path.write_text(json.dumps(state(decisions=[])),encoding='utf-8')
            subprocess.run(['xattr','-w','com.example.task-driver','keep',str(path)],check=True)
            before=path.read_bytes()
            subprocess.run([sys.executable,str(SCRIPT),'next','--state',str(path)],capture_output=True,text=True,check=True)
            attr=subprocess.run(['xattr','-p','com.example.task-driver',str(path)],capture_output=True,text=True,check=True)
            self.assertEqual(before,path.read_bytes());self.assertEqual('keep',attr.stdout.strip())

    def test_inline_state_needs_no_file(self):
        s = state(decisions=[])
        p = subprocess.run([sys.executable, str(SCRIPT), 'next', '--json', json.dumps(s)], capture_output=True, text=True, check=True)
        result = json.loads(p.stdout)
        self.assertEqual('present_plan', result['action'])
        self.assertIn('不等于', result['instruction'])

    def test_invalid_checkpoint_cannot_pass_check(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'state.json'
            path.write_text('{', encoding='utf-8')
            p = subprocess.run([sys.executable, str(SCRIPT), 'check', '--state', str(path)], capture_output=True, text=True)
            self.assertNotEqual(0, p.returncode)
            self.assertFalse(json.loads(p.stdout)['ok'])


if __name__ == '__main__':
    unittest.main()
