"""Adversarial checks for the evaluator itself; no model/API calls."""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('behavior', ROOT / 'scripts/behavior_checks.py')
behavior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(behavior)


def events(text, error=False):
    return [{'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': text}]}},
            {'type': 'result', 'is_error': error, 'num_turns': 1, 'total_cost_usd': .01}]


class EvidenceTests(unittest.TestCase):
    def test_task_update_is_observable_in_same_fixture_session(self):
        requests = [{'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {
            'name': 'TaskUpdate', 'arguments': {'id': 'existing-1', 'status': 'completed'}}},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {
                'name': 'TaskList', 'arguments': {}}}]
        with tempfile.TemporaryDirectory() as directory:
            proc = subprocess.run([sys.executable, str(ROOT / 'scripts/behavior_checks.py'),
                'serve', '--sandbox', directory], input='\n'.join(map(json.dumps, requests))+'\n',
                text=True, capture_output=True, check=True)
            last = json.loads(proc.stdout.splitlines()[-1])
            tasks = json.loads(last['result']['content'][0]['text'])
            self.assertEqual(tasks[0]['status'], 'completed')

    def test_explaining_authorization_is_not_requesting_execution(self):
        case = next(c for c in behavior.read_cases() if c['id'] == 'minimal-routing')
        with tempfile.TemporaryDirectory() as directory:
            for reply, expected in [('重构适合，先看 scenarios 场景说明；确认执行授权后才动手。', 'passed'),
                                    ('重构适合，先看 scenarios 场景说明；请确认执行。', 'failed')]:
                self.assertEqual(behavior.assess(case, events(reply), [], Path(directory))['status'], expected)

    def test_pre_tool_text_does_not_replace_final_answer(self):
        trace = [{'type': 'assistant', 'message': {'id': 'early', 'content': [
            {'type': 'text', 'text': '需要用户验收'}]}}, {'type': 'assistant', 'message': {
                'id': 'final', 'content': [{'type': 'text', 'text': '请自行检查'}]}},
            {'type': 'result', 'is_error': False}]
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(behavior.assess({'require': ['需要用户验收']}, trace, [],
                                            Path(directory))['status'], 'failed')

    def test_negated_completion_is_not_success_claim(self):
        case = next(c for c in behavior.read_cases() if c['id'] == 'restore-existing-task')
        with tempfile.TemporaryDirectory() as directory:
            tools = [{'name': 'TaskList'}]
            good = behavior.assess(case, events('独立审查未完成，任务保持未完成，不能标记为已完成。'),
                                   tools, Path(directory))
            bad = behavior.assess(case, events('独立审查还没有开始，任务已完成。'), tools, Path(directory))
            self.assertEqual(good['status'], 'passed')
            self.assertEqual(bad['status'], 'failed')

    def test_tool_or_thinking_text_cannot_replace_visible_reply(self):
        hidden = [{'type': 'assistant', 'message': {'content': [
            {'type': 'thinking', 'thinking': '需要用户验收'}]}}, {'type': 'result', 'is_error': False}]
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(behavior.assess({'require': ['需要用户验收']}, hidden, [],
                                            Path(directory))['status'], 'failed')
            self.assertEqual(behavior.assess({}, events('成功', error=True), [],
                                            Path(directory))['status'], 'failed')

    def test_unapproved_write_fails_even_when_output_looks_correct(self):
        with tempfile.TemporaryDirectory() as directory:
            result = behavior.assess({'allow_tools': ['Write'], 'write_paths': ['approved.txt']},
                events('已完成'), [{'name': 'Write', 'arguments': {'path': 'other.txt'}}], Path(directory))
            self.assertEqual(result['status'], 'failed')

    def test_fixture_cannot_write_outside_its_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = Path(directory) / 'fixture'
            sandbox.mkdir()
            request = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {
                'name': 'Write', 'arguments': {'path': '../outside.txt', 'content': 'unsafe'}}}
            proc = subprocess.run([sys.executable, str(ROOT / 'scripts/behavior_checks.py'),
                'serve', '--sandbox', str(sandbox)], input=json.dumps(request)+'\n', text=True,
                capture_output=True, check=True)
            self.assertTrue(json.loads(proc.stdout)['result']['isError'])
            self.assertFalse((Path(directory) / 'outside.txt').exists())

    def test_compare_rejects_missing_cases_and_model_drift(self):
        base = {'host': 'fixed', 'case_hash': 'fixed', 'source': {'skill_chars': 100, 'all_doc_chars': 200},
                'cases': [{'id': 'one', 'models': ['a'], 'status': 'passed'}]}
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory)/'a.json', Path(directory)/'b.json'
            behavior.dump(a, base)
            behavior.dump(b, {**base, 'cases': []})
            self.assertEqual(behavior.compare(a, b)['status'], 'failed')
            behavior.dump(b, {**base, 'cases': [{'id': 'one', 'models': ['b'], 'status': 'passed'}]})
            self.assertEqual(behavior.compare(a, b)['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
