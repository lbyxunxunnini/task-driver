import unittest

from test_workflow_control import controller, interruption, state


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
        self.assertEqual([], controller.validate_transition(self.snapshot(refused), self.snapshot(fresh)))
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
