import unittest

from test_workflow_control import controller


class ArchivedBranchTests(unittest.TestCase):
    main = 'origin["原决定"] --> target["当前位置"]'
    entry = dict(id='probe', origin='origin', relation='related', target='target', impact='换位')
    joined = main + '\norigin -.-> probe["调查"] -->|换位| target'

    def test_related_branch_survives_readback(self):
        controller.check_archived_branches(self.joined, [self.entry])
        for graph in (self.main, self.joined.replace('换位', '原样'), self.joined.replace('-.->', '')):
            with self.subTest(graph=graph), self.assertRaises(ValueError):
                controller.check_archived_branches(graph, [self.entry])

    def test_unrelated_conversation_stays_disconnected(self):
        entry = dict(id='calc', origin='origin', relation='unrelated')
        graph = self.main + '\ncalc["计算"] --> result["323"]'
        controller.check_archived_branches(graph, [entry])
        with self.assertRaises(ValueError):
            controller.check_archived_branches(graph + '\nresult --> target', [entry])
