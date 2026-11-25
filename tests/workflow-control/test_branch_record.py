from pathlib import Path
import re
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

    def test_published_discussion_template_and_older_labeled_fork_can_be_archived(self):
        path = Path(__file__).resolve().parents[2] / 'references/templates.md'
        graph = re.search(r'^```mermaid\n(.*?)\n```', path.read_text(), re.M | re.S)[1]
        history = [dict(self.entry, origin='D1', target='D2', impact='证实原取包点已停用')]
        controller.check_archived_branches(graph, history)
        controller.check_archived_branches(graph.replace('D1 -.->', 'D1 -. 调查插问 .->'), history)

    def test_unrelated_conversation_stays_disconnected(self):
        entry = dict(id='calc', origin='origin', relation='unrelated')
        graph = self.main + '\ncalc["计算"] --> result["323"]'
        controller.check_archived_branches(graph, [entry])
        with self.assertRaises(ValueError):
            controller.check_archived_branches(graph + '\nresult --> target', [entry])
