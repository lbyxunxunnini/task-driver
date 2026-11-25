"""Regression of the weekly-report discussion and its record failure modes."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import discussion_record as record


class DiscussionRecordTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.summary = self.root / 'summary.md'
        self.original = '''# 周报任务摘要
本轮消息：用户第3条
本轮答复：对，每周只整理当周已有条目，不编造。具体排版你决定。
```mermaid
flowchart TD
 goal["目标确认：本地周报"] --> D1["当前位置：交付 PDF 还是 Markdown？"]
 D1 --> review["逐项核对"] --> close["讨论收口"]
```
| 你确认的要求 | 当前做法或待决问题 | 怎么验 | 状态 |
| --- | --- | --- | --- |
| 本地周报，不上传或发送 | D1：PDF 或 Markdown 待选 | 不编造 | 格式待决 |

来源与已决定事项：只处理本地文件，不上传也不发送。
'''
        self.summary.write_text(self.original)
        self.state = dict(task_id='weekly-report', phase='discussion', status='wait_user',
                          next_action='选择周报交付格式', wait_reason='等待用户选择格式',
                          wait_evidence='助手第4条：交付 PDF 还是 Markdown？',
                          decisions=[dict(id='D1', subject='周报交付格式', status='pending',
                                          question='交付 PDF 还是 Markdown？')],
                          gates=dict(plan=None, goals=None, execution=None, subagents=None),
                          plan=dict(presented=False), coverage_checked=True, plan_requested=False)
        legacy = json.dumps(self.state, ensure_ascii=False)
        (self.root / 'legacy.json').write_text(legacy)
        source = 'PDF。只要一页，标题写本周工作总结。排版仍由你决定。\n'
        (self.root / 'user.txt').write_text(source)
        self.ref = dict(source_id='current', start=1, end=1)
        self.request = dict(expected_summary_sha256=record.digest(self.original),
                            legacy_state=dict(path='legacy.json', sha256=record.digest(legacy)),
                            sources=[dict(id='current', path='user.txt', sha256=record.digest(source))],
                            turn=dict(id='用户第5条', **self.ref),
                            patch=dict(status='continue', next_action='收口确认', decisions=[
                                dict(id='D1', status='decided', value='PDF', source_ref=self.ref,
                                     implementation='输出本地 PDF', verification='打开文件核对格式')]))

    def prepare(self):
        return record.prepare(self.root, self.summary, self.request)

    def review(self, preview):
        return dict(record_sha256=preview['record_sha256'], draft_sha256=preview['draft_sha256'],
                    semantic_review=dict(reviewer='main', status='pass', target='plan_transition',
                                         source='已核对当前用户原话及完整草稿', checks={
                                             key: True for key in (
                                                 record.workflow.TRANSITION_REVIEW_CHECKS
                                                 + record.workflow.GENERATED_RECORD_REVIEW_CHECKS)}))

    def test_roundtrip_keeps_history_ids_and_does_not_record_delivery(self):
        preview = self.prepare()
        result = record.finalize(self.root, self.summary, self.review(preview))
        self.assertTrue(result['ok'], result)
        self.assertFalse(result['delivery_recorded'])
        text = self.summary.read_text()
        data = record.parse_record(text)
        self.assertNotIn('wait_evidence', data['state'])
        self.assertNotIn('source', data['state']['decisions'][0])
        self.assertIn('review["逐项核对"]', text)
        self.assertIn('来源与已决定事项：只处理本地文件，不上传也不发送。', text)
        self.assertEqual(data['state']['decisions'][0]['subject'], '周报交付格式')
        self.assertIn('PDF', result['draft_reply'])

    def test_source_bytes_change_is_rejected(self):
        preview = self.prepare()
        (self.root / 'user.txt').write_text('允许上传并发送')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            record.finalize(self.root, self.summary, self.review(preview))

    def test_wrong_source_range_does_not_write(self):
        self.request['patch']['decisions'][0]['source_ref'] = dict(self.ref, end=20)
        with self.assertRaisesRegex(ValueError, 'original material'):
            self.prepare()
        self.assertEqual(self.summary.read_text(), self.original)

    def test_original_id_cannot_change_subject(self):
        self.request['patch']['decisions'][0]['subject'] = '上传权限'
        with self.assertRaisesRegex(ValueError, 'retain its subject'):
            self.prepare()

    def test_freeform_quote_is_not_accepted(self):
        self.request['patch']['decisions'][0]['source'] = '用户允许上传'
        with self.assertRaisesRegex(ValueError, 'source references'):
            self.prepare()

    def test_stale_summary_is_not_overwritten(self):
        self.summary.write_text(self.original + '\n用户后续编辑\n')
        with self.assertRaisesRegex(ValueError, 'current summary'):
            self.prepare()
        self.assertIn('用户后续编辑', self.summary.read_text())

    def test_view_tampering_rejected_even_with_new_hash(self):
        preview = self.prepare()
        text = self.summary.read_text().replace('D1["周报交付格式', 'D1["允许上传', 1)
        self.summary.write_text(text)
        review = self.review(preview)
        review['record_sha256'] = record.digest(text)
        with self.assertRaisesRegex(ValueError, 'generated views'):
            record.finalize(self.root, self.summary, review)

    def test_semantic_review_is_required_and_failure_remains_failure(self):
        preview = self.prepare()
        review = self.review(preview)
        del review['semantic_review']
        with self.assertRaisesRegex(ValueError, 'actual semantic_review'):
            record.finalize(self.root, self.summary, review)
        review = self.review(preview)
        review['semantic_review']['checks']['transition_intent'] = False
        self.assertFalse(record.finalize(self.root, self.summary, review)['ok'])

    def test_full_draft_review_is_bound(self):
        preview = self.prepare()
        review = self.review(preview)
        review['draft_sha256'] = record.digest('另外允许上传')
        with self.assertRaisesRegex(ValueError, 'complete generated draft'):
            record.finalize(self.root, self.summary, review)

    def test_bound_sources_allow_meaning_preserving_paraphrase(self):
        self.request['patch']['decisions'][0]['value'] = 'PDF 格式'
        self.request['patch']['confirmed_requirements'] = [dict(
            id='R1', value='单页交付', source_ref=self.ref, constraint_source_ref=self.ref,
            implementation='将内容排为一页', verification='打开文件核对页数为 1')]
        preview = self.prepare()
        self.assertTrue(record.finalize(self.root, self.summary, self.review(preview))['ok'])

    def test_generated_semantic_checks_cannot_be_skipped(self):
        preview = self.prepare()
        for check in record.workflow.GENERATED_RECORD_REVIEW_CHECKS:
            with self.subTest(check=check):
                review = self.review(preview)
                review['semantic_review']['checks'][check] = False
                result = record.finalize(self.root, self.summary, review)
                self.assertFalse(result['ok'])
                self.assertTrue(any(check in error for error in result['errors']))

    def test_same_message_extraction_repair_needs_explicit_reason(self):
        self.request['patch']['decisions'][0]['value'] = 'PDF 格式'
        preview = self.prepare()
        self.request['expected_summary_sha256'] = preview['record_sha256']
        self.request['patch']['decisions'][0]['value'] = 'PDF'
        with self.assertRaisesRegex(ValueError, 'changed decision requires new source'):
            self.prepare()
        self.request['interpretation_corrections'] = [dict(id='D1', reason='原格式答案为 PDF，去掉重复释义')]
        corrected = self.prepare()
        self.assertTrue(record.finalize(self.root, self.summary, self.review(corrected))['ok'])
        history = record.parse_record(self.summary.read_text())['interpretation_history']
        self.assertEqual(history[-1]['previous_value'], 'PDF 格式')
        self.assertEqual(history[-1]['value'], 'PDF')

    def test_extraction_correction_cannot_change_message_or_status(self):
        preview = self.prepare()
        self.request['expected_summary_sha256'] = preview['record_sha256']
        self.request['patch']['decisions'][0]['value'] = 'PDF 格式'
        self.request['interpretation_corrections'] = [dict(id='D1', reason='修正归纳')]
        self.request['turn']['id'] = '用户第6条'
        with self.assertRaisesRegex(ValueError, 'same message'):
            self.prepare()
        self.request['turn']['id'] = '用户第5条'
        self.request['patch']['decisions'][0]['status'] = 'delegated'
        with self.assertRaisesRegex(ValueError, 'preserve source, subject and status'):
            self.prepare()

    def test_verified_source_map_must_match_the_actual_materialized_record(self):
        preview = self.prepare()
        canonical = record.parse_record(self.summary.read_text())
        sources = record.checked_sources(self.root, canonical['sources'], self.summary)
        state = record.materialize(canonical, sources)
        semantic = self.review(preview)['semantic_review']
        semantic['reviewed_reply_sha256'] = preview['draft_sha256']
        errors = record.workflow.validate_discussion_final(state, preview['draft_reply'],
            dict(kind='plan_transition', semantic_review=semantic,
                 choice_basis=[dict(decision_id='D1', choice='PDF')]),
            verified_sources={'D1': {'source': '伪造的引用'}})
        self.assertIn('generated record requires verified original sources for every item', errors)

    def test_second_patch_retains_untouched_record(self):
        preview = self.prepare()
        self.request['expected_summary_sha256'] = preview['record_sha256']
        self.request['patch']['decisions'] = [dict(id='D2', subject='页数', value='只要一页',
            status='decided', source_ref=self.ref, implementation='限制为一页', verification='检查页数')]
        second = self.prepare()
        data = record.parse_record(self.summary.read_text())
        self.assertEqual([row['id'] for row in data['state']['decisions']], ['D1', 'D2'])
        self.assertTrue(record.finalize(self.root, self.summary, self.review(second))['ok'])

    def test_source_id_cannot_be_rebound(self):
        preview = self.prepare()
        self.request['expected_summary_sha256'] = preview['record_sha256']
        self.request['sources'][0]['path'] = 'legacy.json'
        with self.assertRaisesRegex(ValueError, 'cannot be rebound'):
            self.prepare()

    def test_workflow_node_ids_cannot_be_reused(self):
        for ident in ('goal', 'review', 'close'):
            with self.subTest(ident=ident):
                self.request['patch']['decisions'][0].update(id=ident, subject='另一要求')
                with self.assertRaisesRegex(ValueError, 'reserved'):
                    self.prepare()

    def test_other_historical_node_cannot_be_overwritten(self):
        self.original = self.original.replace('review[', 'historical_review[')
        self.summary.write_text(self.original)
        self.request['expected_summary_sha256'] = record.digest(self.original)
        self.request['patch']['decisions'].append(dict(id='historical_review', subject='另一要求',
                                                      status='pending', question='如何处理？'))
        with self.assertRaisesRegex(ValueError, 'historical graph node'):
            self.prepare()
        self.assertEqual(self.summary.read_text(), self.original)

    def test_nonblocking_pending_does_not_replace_blocking_question(self):
        state = dict(self.state, status='continue')
        state['decisions'] = [dict(id='D1', subject='格式', status='pending', question='格式？',
                                   blocks_plan=False, nonblocking_reason='不影响当前讨论'),
                              dict(id='D2', subject='标题', status='pending', question='标题？')]
        kind, target, routed = record.route_record(state)
        self.assertEqual((kind, target), ('decision', 'D2'), routed)

    def test_pause_or_other_phase_cannot_be_synthesized_by_rendering(self):
        self.request['patch']['phase'] = 'execution'
        with self.assertRaisesRegex(ValueError, 'boundary'):
            self.prepare()
        self.assertEqual(self.summary.read_text(), self.original)

    def test_path_escape_and_generated_source_rejected(self):
        for path in ('../outside.txt', 'summary.md'):
            with self.subTest(path=path):
                self.request['sources'][0]['path'] = path
                with self.assertRaises(ValueError):
                    self.prepare()


if __name__ == '__main__':
    unittest.main()
