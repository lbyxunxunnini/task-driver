import hashlib
import json
import subprocess
import sys
import unittest

from test_workflow_control import READ_ONLY_RECORD, SCRIPT, controller, handoff, interruption, state


class InterruptionReturnTests(unittest.TestCase):
    def setUp(self):
        self.parent = state(status='wait_user', wait_reason='选择格式',
                            wait_evidence='助手第18条', next_action='选择导出格式')
        self.frame = interruption(request='计算17×19', branch={'relation': 'unrelated', 'origin': 'discuss'},
                                  resume_point=controller.make_resume_point(self.parent))
        self.closed = dict(self.frame, status='complete', result_evidence='计算结果是323')

    def snapshot(self, frame):
        return dict(self.parent, interruptions=[frame])

    def test_recorded_branch_cannot_disappear_or_be_redirected(self):
        related = {'relation': 'related', 'origin': 'discuss', 'target': 'review', 'impact': '修改验收条件'}
        for branch in (None, {'relation': 'unrelated', 'origin': 'review'}):
            with self.subTest(branch=branch):
                changed = dict(self.closed)
                if branch is None:
                    del changed['branch']
                else:
                    changed['branch'] = branch
                errors = controller.validate_transition(self.snapshot(self.frame), self.snapshot(changed))
                self.assertIn('recorded branch must retain its origin', errors)

    def test_answer_requires_existing_frame_and_preserves_wait_after_return(self):
        closed = self.snapshot(self.closed)
        asked = dict(self.closed, return_question_source='第20条返回提问')
        refused = dict(asked, return_answer='no', return_answer_source='第21条暂不返回')
        agreed = dict(refused, return_answer='yes', return_answer_source='第23条现在返回')
        self.assertTrue(controller.validate_transition(self.parent, self.snapshot(agreed)))
        self.assertTrue(controller.validate_transition(closed, self.snapshot(agreed)))
        previous = closed
        for frame, action in [(asked, 'wait_interruption'), (refused, 'wait_interruption'),
                              (agreed, 'reconcile_interruption')]:
            current = self.snapshot(frame)
            self.assertEqual([], controller.validate_transition(previous, current))
            self.assertEqual(action, controller.route(current)['action'])
            previous = current
        restored = dict(self.parent, branch_history=[controller.branch_record(agreed)])
        self.assertEqual([], controller.validate_transition(previous, restored))
        self.assertEqual('wait_user', controller.route(restored)['action'])

    def test_return_delivers_result_or_cancellation_before_question(self):
        for status, result in [('complete', '17×19 等于 323。'), ('cancelled', '这次计算已取消。')]:
            with self.subTest(status=status):
                snapshot = self.snapshot(dict(self.closed, status=status, result_evidence=result))
                question = controller.route(snapshot)['question']
                self.assertIn('选择导出格式', question)
                self.assertNotIn('助手第18条', question)
                for empty in [question, '**任务驱动 · 讨论阶段**\n\n' + question]:
                    self.assertTrue(controller.validate_discussion_final(snapshot, empty, None))
                self.assertEqual([], controller.validate_discussion_final(snapshot, result + '\n' + question, None))

    def test_resume_uses_saved_question_or_next_action(self):
        for point, expected in [(dict(self.frame['resume_point'], wait_evidence='导出 PDF 吗？'), '导出 PDF 吗'),
                                ({'phase': 'discussion', 'status': 'continue', 'next_action': '讨论范围',
                                  'wait_evidence': None}, '讨论范围')]:
            with self.subTest(point=point):
                current = self.snapshot(dict(self.closed, resume_point=point))
                self.assertEqual([], controller.validate(current))
                result = controller.route(current)
                self.assertEqual('ask_return_to_main', result['action'])
                self.assertIn(expected, result['question'])

    def test_branch_revision_reconciles_new_facts_without_replacing_origin(self):
        changed = dict(self.closed, branch={'relation': 'related', 'origin': 'discuss',
                       'target': 'review', 'impact': '账号缺少权限，影响主任务验收'})
        self.assertIn('branch changes require fresh revision evidence',
                      controller.validate_transition(self.snapshot(self.frame), self.snapshot(changed)))
        changed['branch_revision_source'] = '本轮账号调查：缺少任务所需权限，因此改为相关分支'
        self.assertEqual([], controller.validate(self.snapshot(changed)))
        self.assertEqual([], controller.validate_transition(self.snapshot(self.frame), self.snapshot(changed)))
        self.assertEqual('reconcile_interruption', controller.route(self.snapshot(changed))['action'])
        restored = dict(self.parent, branch_history=[controller.branch_record(changed)])
        self.assertEqual([], controller.validate_transition(self.snapshot(changed), restored))
        self.assertIn('branch_revision_source', restored['branch_history'][0])
        erased = dict(changed)
        erased.pop('branch_revision_source')
        self.assertTrue(controller.validate_transition(self.snapshot(changed), self.snapshot(erased)))
        # A later reversal needs fresh evidence, not the earlier source reused.
        reverse = dict(changed, branch=self.frame['branch'])
        self.assertTrue(controller.validate_transition(self.snapshot(changed), self.snapshot(reverse)))
        reverse['branch_revision_source'] = '后续核对：该账号属于另一项目，与当前任务无关'
        self.assertEqual([], controller.validate_transition(self.snapshot(changed), self.snapshot(reverse)))
        self.assertEqual('ask_return_to_main', controller.route(self.snapshot(reverse))['action'])

    def test_branch_revision_clears_obsolete_return_wait(self):
        refused = dict(self.closed, return_question_source='第20条返回问题',
                       return_answer='no', return_answer_source='第21条不返回')
        changed = dict(refused, branch={'relation': 'related', 'origin': 'discuss',
                       'target': 'review', 'impact': '影响交付'}, branch_revision_source='新调查证据')
        self.assertTrue(controller.validate(self.snapshot(changed)))
        for key in ('return_question_source', 'return_answer', 'return_answer_source'):
            changed.pop(key)
        self.assertEqual([], controller.validate_transition(self.snapshot(refused), self.snapshot(changed)))
        altered = dict(changed, resume_point=dict(changed['resume_point'], next_action='改做另一任务'))
        self.assertTrue(controller.validate_transition(self.snapshot(refused), self.snapshot(altered)))

    def test_direct_return_reuses_user_instruction_without_a_question(self):
        directed = dict(self.frame, return_instruction_source='用户第19条：算完继续讨论导出格式')
        self.assertEqual([], controller.validate_transition(self.parent, self.snapshot(directed)))
        closed = dict(directed, status='complete', result_evidence='计算结果323')
        self.assertEqual([], controller.validate_transition(self.snapshot(directed), self.snapshot(closed)))
        self.assertEqual('reconcile_interruption', controller.route(self.snapshot(closed))['action'])
        restored = dict(self.parent, branch_history=[controller.branch_record(closed)])
        self.assertEqual([], controller.validate_transition(self.snapshot(closed), restored))
        self.assertEqual('wait_user', controller.route(restored)['action'])
        self.assertEqual(self.parent['decisions'], restored['decisions'])
        self.assertEqual(self.parent['gates'], restored['gates'])

    def test_direct_return_does_not_override_a_new_refusal_or_pause(self):
        asked = dict(self.closed, return_question_source='第20条返回问题')
        refused = dict(asked, return_answer='no', return_answer_source='第21条不返回')
        stale = dict(refused, return_instruction_source='第19条算完继续')
        self.assertTrue(controller.validate(self.snapshot(stale)))
        self.assertEqual('wait_interruption', controller.route(self.snapshot(refused))['action'])
        fresh = dict(self.closed, return_instruction_source='第22条：现在继续原任务')
        self.assertTrue(controller.validate_transition(self.snapshot(refused), self.snapshot(fresh)))
        answered = dict(refused, return_answer='yes', return_answer_source=fresh['return_instruction_source'])
        self.assertEqual([], controller.validate_transition(self.snapshot(refused), self.snapshot(answered)))
        for stale_source in ('第19条算完继续', '第21条：肯定'):
            changed = dict(answered, return_answer_source=stale_source)
            self.assertTrue(controller.validate_transition(self.snapshot(refused), self.snapshot(changed)))
        reused = dict(fresh, return_instruction_source=refused['return_answer_source'])
        self.assertTrue(controller.validate_transition(self.snapshot(refused), self.snapshot(reused)))
        paused = dict(self.parent, status='paused', wait_reason='用户暂停原任务')
        closed = dict(fresh, resume_point=controller.make_resume_point(paused))
        restored = dict(paused, branch_history=[controller.branch_record(closed)])
        self.assertEqual([], controller.validate_transition(dict(paused, interruptions=[closed]), restored))
        self.assertEqual('paused', controller.route(restored)['action'])
        resumed = dict(restored, status='continue')
        self.assertIn('resuming paused task requires source',
                      controller.validate_transition(dict(paused, interruptions=[closed]), resumed))

    def test_unsolicited_refusal_and_opaque_message_references(self):
        earlier = '消息定位 kX：算完继续'
        rejected = '确认卡 imZ：先别回原题'
        directed = dict(self.frame, return_instruction_source=earlier)
        refused = dict(self.frame, return_answer='no', return_answer_source=rejected,
                       revoked_return_sources=[earlier])
        closed = dict(refused, status='complete', result_evidence='323')
        self.assertEqual([], controller.validate_transition(self.snapshot(directed), self.snapshot(refused)))
        self.assertEqual([], controller.validate_transition(self.snapshot(refused), self.snapshot(closed)))
        self.assertEqual('deliver_interruption_result', controller.route(self.snapshot(closed))['action'])
        fresh = dict(self.closed, return_instruction_source='新的用户消息 aB：现在继续', revoked_return_sources=[earlier])
        self.assertEqual([], controller.validate_transition(self.snapshot(closed), self.snapshot(fresh)))
        self.assertTrue(controller.validate(self.snapshot(dict(fresh, return_instruction_source=earlier))))
        self.assertTrue(controller.validate_transition(self.snapshot(closed), self.snapshot(dict(fresh, revoked_return_sources=[]))))
        # An older approval is equally stale when supplied as an answer to a real question.
        asked = dict(self.closed, return_question_source='消息定位 h：是否返回')
        approved = dict(asked, return_answer='yes', return_answer_source=earlier)
        refused = dict(asked, return_answer='no', return_answer_source=rejected, revoked_return_sources=[earlier])
        self.assertEqual([], controller.validate_transition(self.snapshot(approved), self.snapshot(refused)))
        stale = dict(refused, return_answer='yes', return_answer_source=earlier)
        self.assertTrue(controller.validate_transition(self.snapshot(refused), self.snapshot(stale)))
        new = dict(refused, return_answer='yes', return_answer_source='新的用户消息 aB：现在继续')
        self.assertEqual([], controller.validate_transition(self.snapshot(refused), self.snapshot(new)))

    def test_message_locator_alias_cannot_reuse_withdrawn_consent_on_either_route(self):
        old = '用户第19条：算完继续'
        no = '用户第21条：先不要继续主任务'
        for asked in (False, True):
            refused = dict(self.closed, return_answer='no', return_answer_source=no, revoked_return_sources=[old])
            if asked:
                refused['return_question_source'] = '助手第20条：是否继续？'
            for candidate, allowed in [('第19条：算完继续', False), ('消息第 21 条：继续', False),
                                       ('第25条：算完继续', True)]:
                with self.subTest(asked=asked, candidate=candidate):
                    if asked:
                        next_frame = dict(refused, return_answer='yes', return_answer_source=candidate)
                    else:
                        next_frame = dict(self.closed, return_instruction_source=candidate, revoked_return_sources=[old])
                    errors = controller.validate_transition(self.snapshot(refused), self.snapshot(next_frame))
                    self.assertEqual(allowed, not errors, errors)

    def test_cli_refusal_delivers_the_result_once_and_waits_for_real_return_consent(self):
        def cli(mode, previous, current, **fields):
            payload = dict(previous=previous, state=current, **fields)
            result = subprocess.run([sys.executable, str(SCRIPT), mode, '--state', '-'],
                                    input=json.dumps(payload), capture_output=True, text=True)
            return json.loads(result.stdout)

        refused = dict(self.frame, return_answer='no', return_answer_source='用户第19条：先别回原题')
        for status, evidence, reply in [('complete', '计算明细\n计算结果是323', '17×19 等于 323。'),
                                        ('cancelled', '用户撤回了临时计算', '本次计算已取消。')]:
            with self.subTest(status=status):
                closed = dict(refused, status=status, result_evidence=evidence)
                previous, current = self.snapshot(refused), self.snapshot(closed)
                result = cli('next', previous, current)
                self.assertEqual(('deliver_interruption_result', status), (result['action'], result['outcome']))
                waived = handoff('waived')
                waived['semantic_review']['checks']['result_delivered'] = True
                waived['semantic_review']['reviewed_reply_sha256'] = hashlib.sha256(reply.encode()).hexdigest()
                final = dict(discussion_record=READ_ONLY_RECORD, discussion_handoff=waived, draft_reply=reply)
                self.assertTrue(cli('final', previous, current, **final)['ok'])
                for bad_reply in ('', reply + ' 回到原题吗？', reply + ' 现在开始执行原任务。'):
                    self.assertFalse(cli('final', previous, current, **dict(final, draft_reply=bad_reply))['ok'])
                self.assertFalse(cli('final', previous, current, **dict(final, discussion_handoff=None))['ok'])
                self.assertNotIn('result_delivery_source', closed)
                for altered in (dict(current, next_action='执行主线任务'),
                                dict(current, gates=dict(current['gates'], execution='插问结果'))):
                    self.assertEqual('repair_state', cli('next', previous, altered)['action'])
                    self.assertFalse(cli('final', previous, altered, **final)['ok'])
                decided = dict(current['decisions'][0], status='decided', value='PDF', source='用户第19条：格式选 PDF')
                self.assertEqual('repair_state', cli('next', previous, dict(current, decisions=[decided]))['action'])
                # Record a genuine main answer from the same message before registering its separate refusal.
                active = self.snapshot(self.frame)
                answered = dict(active, decisions=[decided])
                self.assertTrue(cli('check', active, answered)['ok'])
                rejected = dict(previous, decisions=[decided])
                self.assertTrue(cli('check', answered, rejected)['ok'])
                self.assertEqual('deliver_interruption_result',
                                 cli('next', rejected, dict(current, decisions=[decided]))['action'])
                self.assertFalse(cli('check', active, dict(previous, decisions=[decided]))['ok'])

                sent = dict(closed, result_delivery_source='助手第20条：已送达当前结果')
                waiting = self.snapshot(sent)
                self.assertEqual('wait_interruption', cli('next', current, waiting)['action'])
                self.assertFalse(cli('final', current, waiting, **final)['ok'])
                self.assertEqual('repair_state', cli('next', waiting, current)['action'])
                later = dict(READ_ONLY_RECORD, turn_id='用户第21条', answer='再补充，格式选 PDF。')
                independent = dict(decided, source=later['turn_id'] + '：' + later['answer'])
                updated = dict(waiting, decisions=[independent])
                self.assertTrue(cli('check', waiting, updated, discussion_record=later)['ok'])
                self.assertEqual('wait_interruption', cli('next', updated, updated)['action'])
                self.assertEqual('repair_state', cli('next', waiting, updated)['action'])
                self.assertFalse(cli('check', current, updated, discussion_record=later)['ok'])
                fabricated = dict(waiting, decisions=[dict(independent, source='插问来信')])
                self.assertFalse(cli('check', waiting, fabricated, discussion_record=later)['ok'])
                self.assertFalse(cli('check', waiting, updated)['ok'])
                self.assertFalse(cli('check', waiting, self.snapshot(dict(sent, result_evidence='结果已更改')))['ok'])
                for field, value in [('confirmed_requirements', [dict(id='R1', value='覆盖全部页',
                                      verification='核对文件名', source='插问来信')]),
                                     ('removed_decisions', {'R1': '以插问为撤回依据'}),
                                     ('execution_receipt', '随发送结果授予执行许可')]:
                    self.assertFalse(cli('check', current, dict(waiting, **{field: value}))['ok'])
                history = [controller.branch_record(sent)]
                archived = dict(self.parent, branch_history=history)
                self.assertEqual('repair_state', cli('next', waiting, archived)['action'])

                resumed = dict(sent, return_instruction_source='用户第21条：现在可以回原题')
                del resumed['return_answer'], resumed['return_answer_source']
                approved = self.snapshot(resumed)
                premature_gates = dict(self.parent['gates'], execution=resumed['return_instruction_source'])
                self.assertFalse(cli('check', waiting, dict(approved, gates=premature_gates))['ok'])
                action = cli('next', waiting, approved)
                self.assertEqual('reconcile_interruption', action['action'])
                self.assertEqual(sent['result_delivery_source'], action['result_delivery_source'])
                self.assertEqual(self.frame['resume_point'], action['resume_point'])
                self.assertEqual('wait_user', cli('next', approved, archived)['action'])
                self.assertFalse(cli('check', approved, dict(archived, gates=premature_gates))['ok'])
                paused = dict(waiting, status='paused', wait_reason='用户另行暂停主任务',
                              discussion_question_waiver_source='用户第21条：请先暂停主任务')
                self.assertTrue(cli('next', waiting, paused)['hold_main'])
                self.assertFalse(cli('check', waiting, dict(paused, next_action='执行原计划'))['ok'])
                paused_archive = dict(paused, interruptions=[], branch_history=history)
                self.assertEqual('paused', cli('next', paused, paused_archive)['action'])
                ack = dict(final, draft_reply='原任务已暂停。', discussion_handoff=handoff('waived'))
                self.assertTrue(cli('final', paused, paused_archive, **ack)['ok'])
                repeated = dict(ack, draft_reply=evidence)
                self.assertFalse(cli('final', paused, paused_archive, **repeated)['ok'])

        premature = self.snapshot(dict(refused, result_delivery_source='尚无已送达结果'))
        self.assertEqual('repair_state', cli('next', self.snapshot(refused), premature)['action'])

        outer = interruption(id='first', status='wait_user', next_action='等待第一项决定',
                             wait_reason='等待用户', wait_evidence='助手第12条：请选格式')
        nested = dict(refused, resume_point=controller.make_resume_point(outer))
        before = dict(self.parent, interruptions=[outer, nested])
        complete = dict(nested, status='complete', result_evidence='323')
        self.assertEqual('deliver_interruption_result', cli('next', before,
                         dict(self.parent, interruptions=[outer, complete]))['action'])
        moved = dict(outer, next_action='开始执行第一项任务')
        self.assertEqual('repair_state', cli('next', before,
                         dict(self.parent, interruptions=[moved, complete]))['action'])

        translation = '你今天过得好吗？'
        translated = self.snapshot(dict(refused, status='complete', result_evidence=translation))
        waived = handoff('waived')
        waived['semantic_review']['checks']['result_delivered'] = True
        self.assertTrue(cli('final', self.snapshot(refused), translated, discussion_record=READ_ONLY_RECORD,
                            discussion_handoff=waived, draft_reply=translation)['ok'])
        self.assertFalse(cli('final', self.snapshot(refused), translated, discussion_record=READ_ONLY_RECORD,
                             discussion_handoff=waived, draft_reply=translation + ' 现在回到主线吗？')['ok'])

    def test_cli_delivers_and_archives_only_the_interruption_under_current_hold(self):
        previous = self.snapshot(dict(self.frame, return_instruction_source='用户：做完继续'))
        closed = dict(self.closed, revoked_return_sources=['用户：做完继续'])
        for hold in [dict(status='paused', wait_reason='用户叫停原任务', discussion_question_waiver_source='用户：主任务暂停'),
                     dict(scope_limited=True, scope_limited_source='用户：这轮只交付计算结果，不要再问')]:
            with self.subTest(hold=hold):
                active = dict(self.snapshot(closed), **hold)
                self.assertEqual([], controller.validate_transition(previous, active))
                stale = dict(active, interruptions=[dict(self.closed, return_instruction_source='用户：做完继续')])
                self.assertTrue(controller.validate_transition(previous, stale))
                archived = dict(active, interruptions=[], branch_history=[controller.branch_record(closed)])
                routed = controller.route(active)
                self.assertEqual('reconcile_interruption', routed['action'])
                self.assertTrue(routed['hold_main'])
                for old, new in ((previous, active), (active, archived)):
                    waived = handoff('waived')
                    self.assertTrue(controller.validate_discussion_final(
                        new, '原任务已暂停。', waived, previous=old))
                    waived['semantic_review']['checks']['result_delivered'] = True
                    payload = {'previous': old, 'state': new, 'discussion_record': READ_ONLY_RECORD,
                               'draft_reply': '17×19 等于 323。', 'discussion_handoff': waived}
                    result = subprocess.run([sys.executable, str(SCRIPT), 'final', '--state', '-'],
                                            input=json.dumps(payload), capture_output=True, text=True)
                    self.assertTrue(json.loads(result.stdout)['ok'], result.stdout)
                    self.assertTrue(controller.validate_discussion_final(
                        new, '17×19 等于 323。是否回到原任务？', waived, previous=old))
                lifted = dict(archived, status='continue', scope_limited=False)
                for altered in (lifted, dict(archived, next_action='执行原任务'),
                                dict(archived, gates=dict(archived['gates'], execution='插问返回指令')),
                                dict(archived, branch_history=[])):
                    self.assertTrue(controller.validate_transition(active, altered))

    def test_existing_unrelated_and_nested_handoffs_preserve_independent_main_updates(self):
        answer = dict(self.parent['decisions'][0], status='decided', value='PDF', source='用户另外确认 PDF')
        asked = dict(self.closed, return_question_source='助手问是否返回')
        agreed = dict(asked, return_answer='yes', return_answer_source='用户同意返回')
        current = dict(self.snapshot(agreed), decisions=[answer])
        self.assertEqual([], controller.validate_transition(self.snapshot(asked), current))
        forged = dict(current, gates=dict(current['gates'], execution=agreed['return_answer_source']))
        self.assertTrue(controller.validate_transition(self.snapshot(asked), forged))
        outer = dict(self.closed, return_answer='no', return_answer_source='先不要回主线')
        child = interruption(id='nested', request='补查影响范围的材料', branch={
            'relation': 'related', 'origin': 'discuss', 'target': 'review', 'impact': '影响验收'},
            resume_point=controller.make_resume_point(outer))
        previous = dict(self.parent, interruptions=[outer, child])
        closed = dict(child, status='complete', result_evidence='已核实该范围')
        current = dict(previous, decisions=[answer], interruptions=[outer, closed])
        self.assertEqual([], controller.validate_transition(previous, current))
