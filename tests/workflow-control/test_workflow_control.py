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
             'gates': {'plan': None, 'goals': None, 'execution': None},
             'plan': {'presented': False}, 'coverage_checked': True, 'plan_requested': True, 'plan_request_source': '用户明确要求计划'}
    value.update(updates)
    return value


class ControlTests(unittest.TestCase):
    def test_execution_requires_all_three_evidence_references(self):
        s = state(phase='execution', plan={'presented': True, 'evidence': '计划消息'}, gates={'plan': '用户第 2 轮', 'goals': '用户第 2 轮', 'execution': None})
        self.assertIn('execution evidence required for execution or later', controller.validate(s))
        s['gates']['execution'] = '用户第 2 轮'
        self.assertEqual([], controller.validate(s))

    def test_partial_and_duplicate_decisions(self):
        s = state(status='wait_user', wait_reason='等待验收决定', wait_evidence='上一条消息的验收问题', decisions=[{'id': '1', 'subject': '范围', 'status': 'decided', 'value': '用户选定范围', 'source': '用户第 2 轮'},
                                                  {'id': '2', 'subject': '验收', 'status': 'pending'}])
        self.assertEqual([], controller.validate(s))
        s['decisions'][1]['id'] = '1'
        self.assertIn('decision id missing or duplicated', controller.validate(s))

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

    def test_goal_stage_needs_plan_confirmation_or_combined_view(self):
        s = state(phase='goals', plan={'presented':True,'evidence':'已发送计划'})
        self.assertIn('goals require confirmed plan or combined-view source',controller.validate(s))
        s['combined_view_source'] = '用户明确要求同轮展示计划与目标'
        self.assertEqual([],controller.validate(s))
        del s['combined_view_source']
        s['gates']['plan'] = '用户确认计划'
        self.assertEqual([],controller.validate(s))

    def test_plan_exception_requires_evidence(self):
        s = state(phase='goals', plan_required=False, plan_requested=False)
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
        self.assertEqual('local_complete', controller.route(s)['action'])

    def test_wait_does_not_hide_independent_work(self):
        s = state(status='wait_user', wait_reason='等待回答', wait_evidence='已发出问题', independent_action='检查已有资料')
        self.assertEqual('检查已有资料', controller.route(s)['independent_action'])

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
                  'draft_delivery':{'status':'reported','evidence':'旧草案'}},
                  gates={'plan':'用户确认计划','goals':None,'execution':None})
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
        self.assertIn('unresolved side-effect operation prevents completion',controller.validate(s))
        s.update(status='paused',wait_reason='用户暂停')
        self.assertEqual('paused',controller.route(s)['action'])

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
                gates={'plan':'确认','goals':'确认','execution':'授权'},local_only=True,local_done=False,
                next_action='重试原操作',operations=[op])
        self.assertEqual('check_operation',controller.route(s)['action'])
        op['blocks_next']=False
        self.assertEqual('continue_local',controller.route(s)['action'])
        op['blocks_next']=True;s['local_done']=True
        self.assertEqual('local_complete',controller.route(s)['action'])
        s.update(status='paused',wait_reason='用户暂停')
        self.assertEqual('paused',controller.route(s)['action'])

    def test_duplicate_operations_are_not_treated_as_new_work(self):
        op={'id':'a','reference':'同一个作业','status':'unknown','side_effect':True,'blocks_next':True}
        s=state(operations=[op,dict(op,id='b')])
        self.assertIn('operation reference missing or duplicated',controller.validate(s))

    def test_one_message_can_confirm_plan_goals_and_execution(self):
        s=state(phase='execution',decisions=[],plan={'presented':True,'evidence':'已展示计划'},
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
        new['impact_review']={'reason':'已有授权明确涵盖新范围','retained':['plan','goals','execution']}
        self.assertEqual([],controller.validate_transition(old,new))
        new.pop('impact_review');new['gates']={'plan':'消息3','goals':'消息3','execution':'消息3'}
        self.assertEqual([],controller.validate_transition(old,new))

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
