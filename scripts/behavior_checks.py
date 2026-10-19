#!/usr/bin/env python3
"""Offline contract validation and bounded Claude CLI snapshot replay; stdlib only."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKER = re.compile(r'<!-- behavior-eval\s*(\{.*?\})\s*-->', re.S)


def read_cases():
    cases = []
    for path in sorted((ROOT / 'tests/dialogue-contracts').glob('*.md')):
        blocks = MARKER.findall(path.read_text())
        if not blocks:
            raise ValueError(f'{path.name}: missing replay case')
        for block in blocks:
            case = json.loads(block)
            case['contract'] = str(path.relative_to(ROOT))
            if not case.get('id') or not case.get('prompt'):
                raise ValueError(f'{path.name}: id and prompt required')
            for pattern in case.get('require', []) + case.get('forbid', []):
                re.compile(pattern)
            if case.get('max_turns', 1) not in (1, 2):
                raise ValueError('Only one/two-turn bounded snapshots are supported')
            cases.append(case)
    if len({c['id'] for c in cases}) != len(cases):
        raise ValueError('duplicate case id')
    return cases


def metrics(source):
    names = ['SKILL.md', 'README.md', *[str(p.relative_to(source))
             for p in sorted((source / 'references').glob('*.md'))]]
    texts = {name: (source / name).read_text() for name in names}
    return {'sha256': {n: hashlib.sha256(t.encode()).hexdigest() for n, t in texts.items()},
            'skill_chars': len(texts['SKILL.md']),
            'skill_lines': len(texts['SKILL.md'].splitlines()),
            'all_doc_chars': sum(map(len, texts.values()))}


def check_links():
    """Validate local Markdown links and the protocol's explicit reference paths/anchors."""
    files = [ROOT / 'SKILL.md', ROOT / 'README.md', *sorted((ROOT / 'references').glob('*.md'))]
    for path in files:
        text = path.read_text()
        targets = [(t, False) for t in re.findall(r'\[[^\]]+\]\(([^)]+)\)', text)]
        targets += [(t, True) for t in re.findall(r'`((?:references/|SKILL\.md)[^`\s]*)`', text)]
        for target, root_reference in targets:
            if '://' in target:
                continue
            name, _, anchor = target.partition('#')
            dest = ((ROOT if root_reference else path.parent) / name).resolve() if name else path
            if not dest.is_relative_to(ROOT) or not dest.is_file():
                raise ValueError(f'{path.name}: broken local reference {target}')
            if anchor:
                headings = re.findall(r'^#{1,6}\s+(.+)$', dest.read_text(), re.M)
                slugs = {re.sub(r'[^\w\s-]', '', h.lower()).replace(' ', '-') for h in headings}
                if anchor not in slugs:
                    raise ValueError(f'{path.name}: broken section reference {target}')
    return len(files)


def final_reply(events):
    last = next((e for e in reversed(events) if e.get('type') == 'assistant'), {})
    last_id = last.get('message', {}).get('id')
    return '\n'.join(b.get('text', '') for e in events if e.get('type') == 'assistant'
                      and e.get('message', {}).get('id') == last_id
                      for b in e.get('message', {}).get('content', []) if b.get('type') == 'text')


def assess(case, events, tool_events, sandbox):
    result = next((e for e in reversed(events) if e.get('type') == 'result'), {})
    # Final assistant message only; pre-tool remarks and reasoning cannot satisfy a final reply.
    reply = final_reply(events)
    errors = []
    if not result or result.get('is_error') or not reply.strip():
        errors.append('no successful visible final response')
    for pattern in case.get('require', []):
        if not re.search(pattern, reply):
            errors.append(f'missing response feature: {pattern}')
    for pattern in case.get('forbid', []):
        if re.search(pattern, reply):
            errors.append(f'forbidden response feature: {pattern}')
    names = [e['name'] for e in tool_events]
    for name in names:
        if name not in case.get('allow_tools', []):
            errors.append(f'unexpected tool invocation: {name}')
    for name in case.get('require_tools', []):
        if name not in names:
            errors.append(f'missing tool invocation: {name}')
    write_paths = case.get('write_paths', list(case.get('files', {})))
    for event in tool_events:
        if event['name'] == 'Write' and event.get('arguments', {}).get('path') not in write_paths:
            errors.append('write outside approved fixture path')
    if any(e.get('error') for e in tool_events):
        errors.append('fixture tool rejected an operation')
    for name, content in case.get('files', {}).items():
        path = sandbox / name
        if not path.is_file() or path.read_text() != content:
            errors.append(f'fixture content mismatch: {name}')
    return {'status': 'failed' if errors else 'passed', 'errors': errors,
            'reply': reply, 'tools': names, 'turns': result.get('num_turns'),
            'cost_usd': result.get('total_cost_usd'),
            'usage': result.get('usage', {}), 'models': sorted(result.get('modelUsage', {}))}


def serve(sandbox):
    """Restricted MCP fixture. No shell, network, credentials or production state."""
    definitions = [
        {'name': 'Write', 'description': 'Write a synthetic fixture or summary inside this test directory.',
         'inputSchema': {'type': 'object', 'properties': {'path': {'type': 'string'},
                         'content': {'type': 'string'}}, 'required': ['path', 'content']}},
        {'name': 'TaskList', 'description': 'List this fixture task list.',
         'inputSchema': {'type': 'object', 'properties': {}}},
        {'name': 'TaskUpdate', 'description': 'Update an existing fixture task, preserving its id.',
         'inputSchema': {'type': 'object', 'properties': {'id': {'type': 'string'},
                         'status': {'type': 'string', 'enum': ['in_progress', 'completed']}},
                         'required': ['id', 'status']}}]
    task = {'id': 'existing-1', 'subject': '目标结果', 'status': 'in_progress'}
    for line in sys.stdin:
        request = json.loads(line)
        if 'id' not in request:
            continue
        method = request.get('method')
        if method == 'initialize':
            result = {'protocolVersion': '2025-06-18', 'capabilities': {'tools': {}},
                      'serverInfo': {'name': 'task-driver-fixture', 'version': '1'}}
        elif method == 'tools/list':
            result = {'tools': definitions}
        elif method == 'ping':
            result = {}
        elif method == 'tools/call':
            params = request['params']
            name, args = params['name'], params.get('arguments', {})
            event = {'name': name, 'arguments': args}
            try:
                if name == 'Write':
                    path = (sandbox / args['path']).resolve()
                    if not path.is_relative_to(sandbox.resolve()) or path == sandbox.resolve():
                        raise ValueError('path escapes fixture')
                    if len(args['content']) > 20000:
                        raise ValueError('fixture too large')
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(args['content'])
                    value = {'written': str(path.relative_to(sandbox)), 'content': path.read_text()}
                elif name == 'TaskList':
                    value = [task.copy()]
                elif (name == 'TaskUpdate' and args['id'] == 'existing-1'
                      and args['status'] in ('in_progress', 'completed')):
                    task['status'] = args['status']
                    value = task.copy()
                else:
                    raise ValueError('unknown fixture tool or task')
                result = {'content': [{'type': 'text', 'text': json.dumps(value, ensure_ascii=False)}]}
            except (KeyError, TypeError, ValueError, OSError) as exc:
                event['error'] = str(exc)
                result = {'isError': True, 'content': [{'type': 'text', 'text': str(exc)}]}
            with (sandbox / 'tools.jsonl').open('a') as log:
                log.write(json.dumps(event, ensure_ascii=False) + '\n')
        else:
            print(json.dumps({'jsonrpc': '2.0', 'id': request['id'],
                              'error': {'code': -32601, 'message': 'Method not found'}}), flush=True)
            continue
        print(json.dumps({'jsonrpc': '2.0', 'id': request['id'], 'result': result}), flush=True)


def load_json_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def run(args):
    import fcntl
    source, output = args.source.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / 'report.json').exists():
        raise ValueError('report already exists; use a fresh output directory to preserve evidence')
    cases = read_cases()
    # Bare mode skips user settings. Carry only existing routing/auth environment into the child,
    # without printing credentials, changing configuration, loading hooks or changing providers.
    child_env = os.environ.copy()
    settings = Path.home() / '.claude/settings.json'
    if settings.exists():
        configured = json.loads(settings.read_text()).get('env', {})
        for key in ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_MODEL'):
            if key not in child_env and isinstance(configured.get(key), str):
                child_env[key] = configured[key]
    if args.case:
        cases = [c for c in cases if c['id'] in args.case]
        if set(args.case) != {c['id'] for c in cases}:
            raise ValueError('unknown selected case')
    # Baseline and candidate share this ledger. Reserve before launch; failed runs still count.
    args.ledger.parent.mkdir(parents=True, exist_ok=True)
    with args.ledger.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        lock.seek(0)
        ledger = json.loads(lock.read() or '{"turns_reserved":0,"usd_reserved":0,"runs":[]}')
        report = {'evidence_level': 'real_model_controlled_snapshot', 'source': metrics(source),
                  'host': subprocess.check_output(['claude', '--version'], text=True).strip(),
                  'case_hash': hashlib.sha256(json.dumps(read_cases(), sort_keys=True).encode()).hexdigest(),
                  'cases': [], 'limits': {'turns': args.turn_limit, 'estimated_usd': args.usd_limit}}
        dump(output / 'report.json', report)
        for case in cases:
            if (output / f"{case['id']}.jsonl").exists():
                raise ValueError('output already contains a run; use a fresh directory')
            cap = case.get('max_turns', 1)
            if (ledger['turns_reserved'] + cap > args.turn_limit or
                    ledger['usd_reserved'] + args.per_run_usd > args.usd_limit + 1e-8):
                raise ValueError('shared call/cost reservation exhausted; no model launched')
            ledger['turns_reserved'] += cap
            ledger['usd_reserved'] = round(ledger['usd_reserved'] + args.per_run_usd, 6)
            ledger['runs'].append({'case': case['id'], 'output': str(output), 'max_turns': cap})
            lock.seek(0)
            lock.truncate()
            lock.write(json.dumps(ledger))
            lock.flush()
            with tempfile.TemporaryDirectory(prefix='task-driver-fixture-') as tmp:
                sandbox = Path(tmp)
                mcp = {'mcpServers': {'fixture': {'command': sys.executable,
                       'args': [str(Path(__file__).resolve()), 'serve', '--sandbox', str(sandbox)]}}}
                cmd = ['claude', '--bare', '-p', '--output-format', 'stream-json', '--verbose',
                       '--tools', '', '--strict-mcp-config', '--mcp-config', json.dumps(mcp),
                       '--setting-sources', '', '--disable-slash-commands', '--no-session-persistence',
                       '--permission-mode', 'dontAsk', '--allowedTools', 'mcp__fixture__*',
                       '--max-turns', str(cap), '--max-budget-usd', str(args.per_run_usd),
                       '--system-prompt', (source / 'SKILL.md').read_text()]
                if args.model:
                    cmd += ['--model', args.model]
                # Gold assertions are never sent to the actor. This is a state snapshot, not a UI/session replay.
                prompt = ('你正在继续既有任务。以下是当前任务的恢复事实和用户当前输入；'
                          '除非明确是首次触发，否则入口回复已经完成。'
                          '可用工具是本次隔离目录内的受限工具，其他宿主能力不可用。\n' + case['prompt'])
                start = time.monotonic()
                raw_path = output / f"{case['id']}.jsonl"
                with raw_path.open('w') as raw, (output / f"{case['id']}.stderr").open('w') as err:
                    try:
                        proc = subprocess.run(cmd, input=prompt, text=True, cwd=sandbox,
                                              stdout=raw, stderr=err, timeout=120, env=child_env)
                        returncode = proc.returncode
                    except subprocess.TimeoutExpired:
                        returncode = 124
                events = load_json_lines(raw_path)
                tools_path = sandbox / 'tools.jsonl'
                tools = load_json_lines(tools_path) if tools_path.exists() else []
                assessment = assess(case, events, tools, sandbox)
                assessment.update({'id': case['id'], 'contract': case['contract'],
                                   'duration_seconds': round(time.monotonic() - start, 2),
                                   'returncode': returncode,
                                   'model_calls': len({e['message']['id'] for e in events
                                       if e.get('type') == 'assistant' and not e.get('error')
                                       and e.get('message', {}).get('id')})})
                if returncode:
                    assessment['status'] = 'failed'
                dump(output / f"{case['id']}.tools.json", tools)
                report['cases'].append(assessment)
                dump(output / 'report.json', report)
                print(json.dumps({k: assessment[k] for k in ('id', 'status', 'turns', 'cost_usd', 'errors')},
                                 ensure_ascii=False), flush=True)
                if not any(e.get('type') == 'result' for e in events) or not assessment['models']:
                    raise ValueError('host/API result unavailable; stopped instead of retrying')
                if assessment['cost_usd'] is None or assessment['cost_usd'] > args.per_run_usd:
                    raise ValueError('unknown cost or per-run cap overrun; stopped for review')
                # Preserve comparable model selection across a batch; caller must use this model for candidate.
                if len(assessment['models']) != 1:
                    raise ValueError('unexpected model switch; stop before additional calls')
                if args.model is None:
                    args.model = assessment['models'][0]
        return report


def compare(before, after):
    a, b = json.loads(before.read_text()), json.loads(after.read_text())
    errors = []
    if a['case_hash'] != b['case_hash'] or a['host'] != b['host']:
        errors.append('case definitions or host version changed')
    aa, bb = {c['id']: c for c in a['cases']}, {c['id']: c for c in b['cases']}
    if not aa or aa.keys() != bb.keys():
        errors.append('missing or unpaired cases')
    for key in aa.keys() & bb.keys():
        if bb[key]['models'] != aa[key]['models']:
            errors.append(f'{key}: model changed')
        if bb[key]['status'] != 'passed':
            errors.append(f'{key}: candidate not passed')
    if b['source']['skill_chars'] > a['source']['skill_chars']:
        errors.append('main protocol character budget increased')
    return {'status': 'failed' if errors else 'passed', 'errors': errors,
            'paired_cases': len(aa.keys() & bb.keys()),
            'main_chars': [a['source']['skill_chars'], b['source']['skill_chars']],
            'all_doc_chars': [a['source']['all_doc_chars'], b['source']['all_doc_chars']],
            'boundary': 'Pattern/tool assertions only; five-axis semantic/burden review remains required.'}


def recheck(path, output):
    """Re-score saved replies after fixing an assertion; original raw evidence stays intact."""
    report = json.loads(path.read_text())
    report.setdefault('rechecked_from', str(path.resolve()))
    report.setdefault('original_case_hash', report['case_hash'])
    report['case_hash'] = hashlib.sha256(json.dumps(read_cases(), sort_keys=True).encode()).hexdigest()
    cases = {c['id']: c for c in read_cases()}
    for row in report['cases']:
        case = cases[row['id']]
        evidence = Path(report.get('rechecked_from', str(path))).parent
        row['reply'] = final_reply(load_json_lines(evidence / f"{row['id']}.jsonl"))
        # Keep host/tool/file failures. Only text assertions and approved path scope are rechecked.
        errors = [e for e in row['errors'] if not e.startswith(
            ('missing response feature:', 'forbidden response feature:', 'write outside approved'))]
        for pattern in case.get('require', []):
            if not re.search(pattern, row['reply']):
                errors.append(f'missing response feature: {pattern}')
        for pattern in case.get('forbid', []):
            if re.search(pattern, row['reply']):
                errors.append(f'forbidden response feature: {pattern}')
        tools = json.loads((evidence / f"{row['id']}.tools.json").read_text())
        for event in tools:
            if event['name'] == 'Write' and event['arguments'].get('path') not in case.get(
                    'write_paths', list(case.get('files', {}))):
                errors.append('write outside approved fixture path')
        row['errors'] = errors
        row['status'] = 'failed' if errors or row.get('returncode') else 'passed'
    dump(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check')
    serve_parser = sub.add_parser('serve')
    serve_parser.add_argument('--sandbox', type=Path, required=True)
    runner = sub.add_parser('run')
    runner.add_argument('--source', type=Path, default=ROOT)
    runner.add_argument('--output', type=Path, required=True)
    runner.add_argument('--ledger', type=Path, required=True)
    runner.add_argument('--model')
    runner.add_argument('--case', action='append')
    runner.add_argument('--turn-limit', type=int, default=36)
    runner.add_argument('--usd-limit', type=float, default=4)
    runner.add_argument('--per-run-usd', type=float, default=.12)
    comparison = sub.add_parser('compare')
    comparison.add_argument('baseline', type=Path)
    comparison.add_argument('candidate', type=Path)
    rechecker = sub.add_parser('recheck')
    rechecker.add_argument('report', type=Path)
    rechecker.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.command == 'check':
        print(json.dumps({'contracts': len({c['contract'] for c in read_cases()}),
                          'cases': len(read_cases()), 'linked_documents': check_links(), 'model_calls': 0}))
    elif args.command == 'serve':
        serve(args.sandbox.resolve())
    elif args.command == 'run':
        if not (0 < args.per_run_usd <= args.usd_limit <= 4 and 0 < args.turn_limit <= 36):
            raise ValueError('expected positive caps: per-run <= total <= US$4, turns <= 36')
        report = run(args)
        return int(any(c['status'] != 'passed' for c in report['cases']))
    elif args.command == 'recheck':
        report = recheck(args.report, args.output)
        print(json.dumps({'cases': len(report['cases']), 'passed': sum(
            c['status'] == 'passed' for c in report['cases']), 'model_calls': 0}))
    else:
        value = compare(args.baseline, args.candidate)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return int(value['status'] != 'passed')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f'behavior-checks: {error}', file=sys.stderr)
        sys.exit(1)
