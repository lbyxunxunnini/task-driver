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
    def assess_reply(self, case_id, reply):
        case = next(c for c in behavior.read_cases() if c['id'] == case_id)
        with tempfile.TemporaryDirectory() as directory:
            return behavior.assess(case, events(reply), [], Path(directory))

    def test_choice_question_rejects_missing_options_impacts_or_recommendation_reason(self):
        good = ('这份文档覆盖哪一部分？\n'
                '1. 完整链路（推荐）：包含手动对话到确认卡及自动配对测评，可以从头照着操作。\n'
                '2. 仅自动配对测评：篇幅更短，但不说明手动对话和确认卡的获得过程。\n'
                '推荐1，因为你要求记录整个流程，需要覆盖手动和自动两个部分。')
        bad = [
            '这份文档要同时包含手动终端对话直到确认卡，还是只写本次的10组双模型自动配对测评？',
            '1. 完整链路（推荐）\n2. 自动配对测评\n推荐1，因为你要求记录整个流程，需要覆盖两个部分。',
            good.replace('推荐1，因为你要求记录整个流程，需要覆盖手动和自动两个部分。', '推荐1，更合适。'),
            good.replace('（推荐）', '').replace('推荐1，因为', '原因是'),
        ]
        result = self.assess_reply('discussion-options', good)
        self.assertEqual(result['status'], 'passed', result['errors'])
        self.assertEqual(result['semantic_review'], 'not_performed')
        self.assertTrue(result['manual_checks'])
        alternate = good.replace('推荐1，因为你要求记录整个流程，需要覆盖手动和自动两个部分。',
                                 '因为你要记录整个流程，手动和自动两部分都要覆盖，所以推荐1。')
        self.assertEqual(self.assess_reply('discussion-options', alternate)['status'], 'passed')
        for reply in bad:
            with self.subTest(reply=reply):
                self.assertEqual(self.assess_reply('discussion-options', reply)['status'], 'failed')

    def test_settled_document_scope_does_not_reopen_audience_question(self):
        good = ('已确认手动对话到确认卡和自动配对测评均纳入详细操作文档。\n'
                '1. 生成计划（推荐）。\n2. 继续讨论。\n'
                '推荐1，因为两部分覆盖范围已经确认，当前没有其他未闭合的关键取舍。')
        self.assertEqual(self.assess_reply('document-scope-settled', good)['status'], 'passed')
        logged = ('已确认文档覆盖自动配对测评和手动对话直到确认卡。'
                  '这份文档主要给你自己在终端操作，还是给刚接手项目的同事照着执行？')
        self.assertEqual(self.assess_reply('document-scope-settled', logged)['status'], 'failed')
        # An otherwise complete reply cannot tack on the unnecessary question.
        self.assertEqual(self.assess_reply('document-scope-settled', good + '\n' + logged)['status'], 'failed')

    def test_first_turn_can_produce_requested_plan_without_discussion_restart(self):
        good = ('# 计划草案\n## 1. 桌面按钮对齐\n### 已确认\n只修错位。\n'
                '### 实施方案\n调整对齐约束，保留其他样式。\n'
                '## 2. 移动端窄屏溢出\n### 已确认\n只修容器。\n'
                '### 实施方案\n调整容器约束。仅展示计划，尚未执行。')
        self.assertEqual(self.assess_reply('first-turn-plan', good)['status'], 'passed')
        restart = ('当前环节：讨论\n已识别事项：桌面与移动端修复。\n'
                   '当前讨论：已确认范围和实施方案，是否先讨论文档受众？')
        self.assertEqual(self.assess_reply('first-turn-plan', restart)['status'], 'failed')
        self.assertEqual(self.assess_reply('first-turn-plan', good + '\n我现在开始执行。')['status'], 'failed')
        promise = '已确认桌面和移动端范围，我会生成计划，实施方案是调整对齐约束和容器约束，不统一样式。'
        self.assertEqual(self.assess_reply('first-turn-plan', promise)['status'], 'failed')

    def test_plan_headers_without_actual_implementation_do_not_pass(self):
        empty = '已确认：对齐、容器。\n实施方案：后面再定。'
        self.assertEqual(self.assess_reply('plan-only', empty)['status'], 'failed')
        good = ('## 1. 桌面按钮错位\n### 已确认\n只修按钮位置。\n'
                '### 实施方案\n调整父布局的对齐约束，修复错位，不统一其他按钮样式。\n'
                '## 2. 移动端溢出\n### 已确认\n不改变按钮自身样式。\n'
                '### 实施方案\n调整容器约束适配窄屏，保留其他按钮的原有行为。')
        self.assertEqual(self.assess_reply('plan-only', good)['status'], 'passed')

    def test_acceptance_requires_actionable_steps_instead_of_only_keywords(self):
        vague = '需要用户验收。1. 自己检查一下。通过条件：正常。请反馈。'
        self.assertEqual(self.assess_reply('human-acceptance', vague)['status'], 'failed')
        good = ('需要用户验收：我无法访问指定真机，目标仍未完成。\n'
                '1. 在指定设备安装并打开本次构建，预期正常进入目标页面。\n'
                '2. 在该页面连续点击和滑动，预期触控跟手，没有卡顿或无响应。\n'
                '通过条件：上述操作均流畅，原功能正常。请反馈通过或不通过；'
                '不通过时附设备型号、系统版本与复现步骤。')
        result = self.assess_reply('human-acceptance', good)
        self.assertEqual(result['status'], 'passed', result['errors'])
        self.assertEqual(result['semantic_review'], 'not_performed')

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
