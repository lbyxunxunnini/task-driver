"""Exercise the shared summary through prepare, review, and concurrent saves."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

import test_discussion_record as fixtures


record = fixtures.record


class DiscussionRecordIOTests(unittest.TestCase):
    def setUp(self):
        self.case = fixtures.DiscussionRecordTests()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def request_views(self, *views):
        case = self.case
        source = case.root / 'user.txt'
        wording = '和'.join({'graph': '图', 'table': '表'}[view] for view in views)
        source.write_text(source.read_text() + '请展示本轮的' + wording + '。\n')
        case.request['sources'][0]['sha256'] = record.digest(source.read_bytes())
        case.request['turn']['end'] = 2
        case.request['overview'] = {'views': list(views), 'source_ref': dict(case.ref, start=2, end=2)}

    def test_crlf_from_cli_inspection_through_final_review(self):
        case = self.case
        case.summary.write_bytes(case.original.replace('\n', '\r\n').encode())
        result = subprocess.run(
            [sys.executable, record.__file__, 'inspect', '--project', str(case.root),
             '--summary', case.summary.name], capture_output=True, text=True, check=True)
        case.request['expected_summary_sha256'] = json.loads(result.stdout)['record_sha256']
        preview = case.prepare()
        saved = case.summary.read_bytes()
        self.assertIn(b'\r\n', saved)
        self.assertNotIn(b'\n', saved.replace(b'\r\n', b''))
        self.assertEqual(record.digest(saved), preview['record_sha256'])
        self.assertTrue(record.finalize(case.root, case.summary, case.review(preview))['ok'])
        case.summary.write_bytes(saved.replace(b'\r\n', b'\n'))
        with self.assertRaisesRegex(ValueError, 'changed after preview'):
            record.finalize(case.root, case.summary, case.review(preview))

    def test_competing_prepares_can_only_commit_one_revision(self):
        case = self.case
        first = dict(case.request, introduction='第一次修改')
        second = dict(case.request, introduction='另一处修改')
        reached_replace = threading.Event()
        release = threading.Event()
        both_files_ready = threading.Event()
        original_replace = record.os.replace
        original_fsync = record.os.fsync

        def delay_first_replace(src, dst):
            if not reached_replace.is_set():
                reached_replace.set()
                self.assertTrue(release.wait(5))
            return original_replace(src, dst)

        def note_second_writer_ready(fd):
            original_fsync(fd)
            if reached_replace.is_set():
                both_files_ready.set()

        with ThreadPoolExecutor(2) as pool, patch.object(record.os, 'replace', delay_first_replace), \
                patch.object(record.os, 'fsync', note_second_writer_ready):
            winner = pool.submit(record.prepare, case.root, case.summary, first)
            try:
                self.assertTrue(reached_replace.wait(5))
                loser = pool.submit(record.prepare, case.root, case.summary, second)
                self.assertTrue(both_files_ready.wait(5))
            finally:
                release.set()
            preview = winner.result()
            with self.assertRaisesRegex(ValueError, 'changed concurrently'):
                loser.result()
        self.assertEqual(preview['record_sha256'], record.digest(case.summary.read_bytes()))
        self.assertIn('第一次修改', preview['draft_reply'])

    def test_each_requested_view_is_exact_and_applies_to_this_reply(self):
        case = self.case
        original = deepcopy(case.request)
        for views in (['graph'], ['table'], ['graph', 'table']):
            with self.subTest(views=views):
                case.summary.write_text(case.original)
                (case.root / 'user.txt').write_text('交付 PDF。\n')
                case.request = deepcopy(original)
                self.request_views(*views)
                preview = case.prepare()
                result = record.finalize(case.root, case.summary, case.review(preview))
                self.assertTrue(result['ok'], result)
                for name, pattern in [('graph', record.GRAPH), ('table', record.TABLE)]:
                    block = pattern.search(preview['summary_readback'])[0].strip()
                    self.assertEqual(name in views, block in result['draft_reply'])
                case.request.pop('overview')
                case.request['expected_summary_sha256'] = preview['record_sha256']
                next_preview = case.prepare()
                self.assertFalse(record.workflow.contains_internal_overview(next_preview['draft_reply']))

    def test_pending_question_in_requested_table_is_not_a_second_handoff(self):
        case = self.case
        self.request_views('table')
        case.request['patch']['decisions'] = []
        case.request['patch']['confirmed_requirements'] = [
            dict(id='D2', value='只要一页', source_ref=case.ref)]
        preview = case.prepare()
        self.assertEqual('decision', preview['kind'])
        review = case.review(preview)
        review['semantic_review'].update(
            target='decision', decision_id=preview['decision_id'],
            checks=dict.fromkeys(record.workflow.DECISION_REVIEW_CHECKS +
                                 record.workflow.GENERATED_RECORD_REVIEW_CHECKS, True))
        result = record.finalize(case.root, case.summary, review)
        self.assertTrue(result['ok'], result)
        self.assertEqual(2, result['draft_reply'].count('交付 PDF 还是 Markdown？'))

    def test_previous_view_request_cannot_be_reused_on_a_new_turn(self):
        case = self.case
        self.request_views('graph')
        preview = case.prepare()
        source = case.root / 'next.txt'
        source.write_text('这次请用文字说明。')
        case.request['sources'].append(dict(id='next', path='next.txt', sha256=record.digest(source.read_bytes())))
        case.request['expected_summary_sha256'] = preview['record_sha256']
        case.request['turn'] = dict(id='用户第6条', source_id='next', start=1, end=1)
        with self.assertRaisesRegex(ValueError, 'current user message'):
            case.prepare()
        self.assertEqual(preview['record_sha256'], record.digest(case.summary.read_bytes()))

    def test_missing_original_request_and_later_source_edits_fail_closed(self):
        case = self.case
        self.request_views('graph')
        case.request['overview']['source_ref']['end'] = 99
        with self.assertRaisesRegex(ValueError, 'original material'):
            case.prepare()
        self.assertEqual(case.original, case.summary.read_text())
        case.request['overview']['source_ref']['end'] = 2
        preview = case.prepare()
        (case.root / 'user.txt').write_text('请不要展示图。')
        with self.assertRaisesRegex(ValueError, 'original source changed'):
            record.finalize(case.root, case.summary, case.review(preview))
