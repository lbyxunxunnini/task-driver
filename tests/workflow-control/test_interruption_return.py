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
        for branch in (None, related, {'relation': 'unrelated', 'origin': 'review'}):
            with self.subTest(branch=branch):
                changed = dict(self.closed)
                if branch is None:
                    del changed['branch']
                else:
                    changed['branch'] = branch
                errors = controller.validate_transition(self.snapshot(self.frame), self.snapshot(changed))
                self.assertIn('recorded branch must retain its relation and origin', errors)

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
