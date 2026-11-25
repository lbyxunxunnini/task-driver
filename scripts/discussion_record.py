#!/usr/bin/env python3
"""Maintain one discussion record and derive its readable/checker projections.

Sources are references to externally supplied original material, not authenticated
by this program. The host must protect those files from the responding model.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

import workflow_control as workflow


START = '<!-- task-driver:record:v1 -->'
END = '<!-- /task-driver:record -->'
BLOCK = re.compile(re.escape(START) + r'\n```json\n(.*?)\n```\n' + re.escape(END), re.S)
GRAPH = re.compile(r'```mermaid\n(.*?)\n```', re.S)
TABLE = re.compile(r'^\| 你确认的要求 \| 当前做法或待决问题 \| 怎么验 \| 状态 \|\n(?:\|[^\n]*\|\n?)+', re.M)
RESOLVED = {'decided', 'delegated', 'excluded'}
CLOSURE = '是否结束讨论并开始展示正式计划和验收目标？'


def digest(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def local_path(project, value):
    if not isinstance(value, str) or not value:
        raise ValueError('a project-relative file path is required')
    path = (project / value).resolve()
    if project not in path.parents:
        raise ValueError('path must remain inside the project')
    return path


def load_json(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('JSON input must be an object')
    return value


def parse_record(text):
    matches = list(BLOCK.finditer(text))
    if not matches:
        if START in text or END in text:
            raise ValueError('incomplete canonical record block')
        return None
    if len(matches) != 1 or text.count(START) != 1 or text.count(END) != 1:
        raise ValueError('exactly one canonical record is required')
    record = json.loads(matches[0][1])
    if not isinstance(record, dict) or record.get('version') != 1:
        raise ValueError('unsupported canonical record version')
    return record


def checked_sources(project, sources, summary):
    if not isinstance(sources, list):
        raise ValueError('sources must be a list of original file references')
    result = {}
    for source in sources:
        if not isinstance(source, dict) or set(source) != {'id', 'path', 'sha256'}:
            raise ValueError('source requires id, path and sha256')
        ident = source['id']
        if not isinstance(ident, str) or not ident or ident in result:
            raise ValueError('source ids must be nonempty and unique')
        path = local_path(project, source['path'])
        if path == summary or not path.is_file():
            raise ValueError('source must be an original file, not the generated summary')
        data = path.read_bytes()
        if digest(data) != source['sha256']:
            raise ValueError('original source changed: ' + ident)
        result[ident] = data.decode('utf-8').splitlines()
    return result


def excerpt(reference, sources):
    if not isinstance(reference, dict) or set(reference) != {'source_id', 'start', 'end'}:
        raise ValueError('source_ref requires source_id and inclusive start/end lines')
    lines = sources.get(reference['source_id'])
    start, end = reference['start'], reference['end']
    if (lines is None or type(start) is not int or type(end) is not int
            or not 1 <= start <= end <= len(lines)):
        raise ValueError('source_ref does not address original material')
    return ' '.join(lines[start - 1:end]).strip()


def materialize(record, sources):
    state = deepcopy(record['state'])
    for group in ('decisions', 'confirmed_requirements'):
        for row in state.get(group, []):
            if 'source_ref' in row:
                row['source'] = excerpt(row.pop('source_ref'), sources)
            elif row.get('status') in RESOLVED or group == 'confirmed_requirements':
                raise ValueError('resolved record requires original source_ref: ' + str(row.get('id')))
            if 'constraint_source_ref' in row:
                row['constraint_source'] = excerpt(row.pop('constraint_source_ref'), sources)
            if row.get('implementation') and row.get('verification'):
                # These are explicitly model-proposed details, never user quotations.
                row['detail_source'] = ('模型方案（未执行）：' + row['implementation']
                                        + '；验法：' + row['verification'])
    for key in list(state):
        if key.endswith('_source_ref'):
            state[key[:-4]] = excerpt(state.pop(key), sources)
    return state


def merge_patch(previous, patch):
    if not isinstance(patch, dict):
        raise ValueError('patch must be an object')
    state = deepcopy(previous)
    forbidden = {'task_id', 'phase', 'gates', 'plan', 'goals', 'execution_begun',
                 'execution_receipt', 'branch_history', 'interruptions', 'discussion_closed',
                 'wait_evidence', 'discussion_closure_question_source'}
    for key, value in patch.items():
        if key in forbidden and value != state.get(key):
            raise ValueError('discussion renderer cannot change this boundary: ' + key)
        if key.endswith('_source') and value != state.get(key):
            raise ValueError('use an original *_source_ref rather than free text: ' + key)
        if key not in ('decisions', 'confirmed_requirements'):
            state[key] = deepcopy(value)
            continue
        if not isinstance(value, list):
            raise ValueError(key + ' updates must be a list')
        records = state.setdefault(key, [])
        by_id = {row['id']: row for row in records}
        seen = set()
        for update in value:
            if not isinstance(update, dict) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', str(update.get('id', ''))):
                raise ValueError('record update requires a stable id')
            ident = update['id']
            if ident in ('goal', 'review', 'close'):
                raise ValueError('decision id is reserved for a workflow node: ' + ident)
            if ident in seen:
                raise ValueError('duplicate record update: ' + ident)
            seen.add(ident)
            if any(field in update for field in ('source', 'detail_source', 'constraint_source')):
                raise ValueError('supply source references; repeated source/detail text is generated')
            old = by_id.get(ident)
            if old is not None:
                if 'subject' in update and update['subject'] != old.get('subject'):
                    raise ValueError('an existing id must retain its subject: ' + ident)
                if any(update.get(field, old.get(field)) != old.get(field)
                       for field in ('value', 'status')) and 'source_ref' not in update:
                    raise ValueError('changed decision requires an original source_ref: ' + ident)
                old.update(deepcopy(update))
            else:
                if not update.get('subject') and key == 'decisions':
                    raise ValueError('new decision requires its subject')
                records.append(deepcopy(update))
                by_id[ident] = records[-1]
    # A response being prepared is not evidence of its delivery.
    if state.get('status') == 'continue':
        for key in ('wait_evidence', 'wait_reason', 'discussion_closure_question_source'):
            state.pop(key, None)
    return state


def route_record(state):
    if state.get('phase') != 'discussion' or state.get('interruptions'):
        raise ValueError('use the existing workflow for other phases or active interruptions; record not modified')
    routed = workflow.route(state)
    if routed.get('errors'):
        raise ValueError(json.dumps(routed, ensure_ascii=False))
    action = routed.get('action')
    if action == 'request_plan_transition':
        return 'plan_transition', None, routed
    if action == 'paused':
        return 'waived', None, routed
    pending = [row for row in state.get('decisions', [])
               if row.get('status') == 'pending' and row.get('blocks_plan', True) is not False]
    if pending and action in ('resolve_pending', 'continue_discussion', 'wait_user'):
        return 'decision', pending[0]['id'], routed
    raise ValueError('renderer does not own this handoff; use existing workflow: ' + str(action))


def rows_for(state):
    rows = []
    for group in ('confirmed_requirements', 'decisions'):
        for row in state.get(group, []):
            rows.append((row, 'confirmed' if group == 'confirmed_requirements' else row['status']))
    return rows


def generate_graph(template, state, kind, decision_id):
    # Keep existing topology, unknown nodes and historical branches. Only known
    # decision labels/current position and new decision edges are projections.
    graph = template.replace('当前位置：', '').replace('当前位置:', '')
    if not re.search(r'(?<![\w-])goal\[', graph):
        graph += '\n goal["目标"]'
    for row in state.get('decisions', []):
        ident = row['id']
        label = row['subject'] + '：' + str(row.get('value') or row.get('question') or row['status'])
        if ident == decision_id:
            label = '当前位置：' + label
        definition = ident + '["' + workflow.mermaid_text(label) + '"]'
        # Current-position punctuation must remain visible to the existing checker.
        definition = definition.replace('当前位置#65306;', '当前位置：')
        pattern = r'(?<![\w-])' + re.escape(ident) + r'\[(?:"[^"\n]*"|[^\]\n]*)\]'
        graph, count = re.subn(pattern, lambda match: definition, graph)
        if not count:
            graph += '\n goal --> ' + definition
        for dependency in row.get('depends_on', []):
            if dependency not in {item['id'] for item in state.get('decisions', [])}:
                raise ValueError('unknown decision dependency: ' + dependency)
            graph += '\n ' + dependency + ' --> ' + ident
    if kind != 'decision':
        label = '当前位置：待发送收口问题' if kind == 'plan_transition' else '当前位置：暂停'
        pattern = r'(?<![\w-])close\[(?:"[^"\n]*"|[^\]\n]*)\]'
        graph, count = re.subn(pattern, lambda match: 'close["' + label + '"]', graph)
        if not count:
            graph += '\n goal --> close["' + label + '"]'
    return graph.strip()


def generate_table(state):
    names = {'pending': '待答', 'decided': '已决定', 'delegated': '已委托',
             'excluded': '已排除', 'confirmed': '已确认'}
    lines = ['| 你确认的要求 | 当前做法或待决问题 | 怎么验 | 状态 |', '| --- | --- | --- | --- |']
    for row, status in rows_for(state):
        cells = [row['id'] + ' ' + str(row.get('value') or row.get('subject')),
                 row.get('implementation') or row.get('question') or '待形成做法',
                 row.get('verification') or '待明确验法', names.get(status, status)]
        lines.append('| ' + ' | '.join(str(cell).replace('|', r'\|').replace('\n', ' ') for cell in cells) + ' |')
    return '\n'.join(lines)


def draft_for(record, state, kind, decision_id):
    parts = ['**任务驱动 · 讨论阶段**']
    introduction = record.get('introduction', '').strip()
    if introduction:
        parts.append(introduction)
    if kind == 'plan_transition':
        for row, status in rows_for(state):
            if status not in RESOLVED | {'confirmed'}:
                continue
            label = row.get('value') or row.get('subject')
            if row.get('business_context'):
                label += '（' + row['business_context'] + '）'
            if not row.get('implementation') or not row.get('verification'):
                raise ValueError('supply implementation and verification once: ' + row['id'])
            parts.append(f"- {label}：{row['implementation']}，核验时{row['verification']}。")
        parts.append(CLOSURE)
    elif kind == 'decision':
        row = next(item for item in state['decisions'] if item['id'] == decision_id)
        parts.append(row['question'])
    elif not introduction:
        raise ValueError('paused response requires a scoped explanation')
    return '\n\n'.join(parts)


def render(record, state, kind, decision_id, sources):
    text = record['legacy_text']
    graph = generate_graph(record['graph_template'], state, kind, decision_id)
    text, ngraph = GRAPH.subn(lambda match: '```mermaid\n' + graph + '\n```', text)
    text, ntable = TABLE.subn(lambda match: generate_table(state) + '\n', text)
    if ngraph != 1 or ntable != 1:
        raise ValueError('legacy summary must contain one supported Mermaid block and one requirement table')
    answer = excerpt({key: value for key, value in record['turn'].items() if key != 'id'}, sources)
    for label, value in [('本轮消息', record['turn']['id']), ('本轮答复', answer)]:
        text, count = re.subn('^' + label + r'：.*$', lambda match: label + '：' + value, text, flags=re.M)
        if count != 1:
            raise ValueError('summary requires exactly one ' + label)
    canonical = START + '\n```json\n' + json.dumps(record, ensure_ascii=False, indent=2) + '\n```\n' + END
    return text.rstrip() + '\n\n' + canonical + '\n', answer


def atomic_write(path, text, expected):
    path.parent.mkdir(parents=True, exist_ok=True)
    if digest(path.read_bytes()) != expected:
        raise ValueError('summary changed concurrently; reread before retrying')
    fd, temporary = tempfile.mkstemp(prefix='.discussion-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if digest(path.read_bytes()) != expected:
            raise ValueError('summary changed concurrently; reread before retrying')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def verify_interpretation_corrections(record, previous_raw, request, previous_turn):
    """Allow explicit same-message extraction repairs, never a new user decision."""
    corrections = request.get('interpretation_corrections', [])
    if not isinstance(corrections, list):
        raise ValueError('interpretation_corrections must be a list of id/reason objects')
    if not corrections:
        return set()
    state = record['state']
    if (previous_turn != record['turn'] or state.get('phase') != 'discussion'
            or state.get('status') != 'continue'
            or state.get('plan', {}).get('presented') is True
            or state.get('execution_begun') is True):
        raise ValueError('interpretation correction requires the same message before plan/execution')
    previous_rows = {row['id']: row for row in previous_raw.get('decisions', [])}
    rows = {row['id']: row for row in state.get('decisions', [])}
    verified = set()
    for correction in corrections:
        if (not isinstance(correction, dict) or set(correction) != {'id', 'reason'}
                or not isinstance(correction['reason'], str) or not correction['reason'].strip()):
            raise ValueError('interpretation correction requires its id and actual reason')
        ident = correction['id']
        old, new = previous_rows.get(ident), rows.get(ident)
        if (ident in verified or old is None or new is None or not old.get('source_ref')
                or any(old.get(key) != new.get(key) for key in ('source_ref', 'subject', 'status'))
                or old.get('value') == new.get('value')):
            raise ValueError('interpretation correction must preserve source, subject and status: ' + str(ident))
        verified.add(ident)
        record.setdefault('interpretation_history', []).append({
            'id': ident, 'turn': deepcopy(record['turn']), 'source_ref': deepcopy(new['source_ref']),
            'previous_value': old.get('value'), 'value': new.get('value'), 'reason': correction['reason']})
    return verified


def prepare(project, summary, request):
    original = summary.read_text(encoding='utf-8')
    expected = request.get('expected_summary_sha256')
    if digest(original) != expected:
        raise ValueError('expected_summary_sha256 must match the current summary')
    record = parse_record(original)
    migrating = record is None
    if record is None:
        legacy = request.get('legacy_state', {})
        path = local_path(project, legacy.get('path'))
        if digest(path.read_bytes()) != legacy.get('sha256'):
            raise ValueError('legacy state must match its observed hash')
        graphs = list(GRAPH.finditer(original))
        if len(graphs) != 1:
            raise ValueError('legacy graph cannot be migrated without loss')
        record = {'version': 1, 'state': load_json(path), 'sources': [],
                  'legacy_text': original, 'graph_template': graphs[0][1]}
    else:
        old_sources = checked_sources(project, record['sources'], summary)
        old_state = materialize(record, old_sources)
        old_kind, old_target, _ = route_record(old_state)
        if render(record, old_state, old_kind, old_target, old_sources)[0] != original:
            raise ValueError('generated views changed outside the canonical record')
    registered = {source['id']: source for source in record['sources']}
    for source in request.get('sources', []):
        if source['id'] in registered and source != registered[source['id']]:
            raise ValueError('an original source id cannot be rebound')
        registered[source['id']] = source
    record['sources'] = list(registered.values())
    sources = checked_sources(project, record['sources'], summary)
    previous = deepcopy(record['state']) if migrating else materialize(record, sources)
    previous_raw = deepcopy(record['state'])
    previous_turn = deepcopy(record.get('turn'))
    record['state'] = merge_patch(record['state'], request.get('patch', {}))
    previous_ids = {row['id'] for row in previous.get('decisions', [])}
    for row in record['state'].get('decisions', []):
        if row['id'] not in previous_ids and re.search(
                r'(?<![\w-])' + re.escape(row['id']) + r'\[', record['graph_template']):
            raise ValueError('new decision id collides with a historical graph node: ' + row['id'])
    record['turn'] = request['turn']
    if (not isinstance(record['turn'], dict)
            or not isinstance(record['turn'].get('id'), str)
            or not record['turn']['id'].strip()
            or len(record['turn']['id'].splitlines()) != 1):
        raise ValueError('turn requires a single-line actual message id')
    record['introduction'] = request.get('introduction', '')
    corrections = verify_interpretation_corrections(record, previous_raw, request, previous_turn)
    state = materialize(record, sources)
    issues = workflow.validate(state) + workflow.validate_transition(
        previous, state, verified_corrections=corrections)
    if issues:
        raise ValueError(json.dumps(issues, ensure_ascii=False))
    kind, target, routed = route_record(state)
    text, answer = render(record, state, kind, target, sources)
    draft = draft_for(record, state, kind, target)
    # Check the generated document before replacing the only record.
    with tempfile.TemporaryDirectory(dir=project) as directory:
        trial = Path(directory) / 'summary.md'
        trial.write_text(text, encoding='utf-8')
        workflow.check_final_record({'project': str(project), 'summary': str(trial),
                                     'turn_id': record['turn']['id'], 'answer': answer},
                                    state.get('branch_history', []), decision_ids=[row['id'] for row in state['decisions']])
    atomic_write(summary, text, expected)
    return {'ok': True, 'action': routed['action'], 'kind': kind, 'decision_id': target,
            'record_sha256': digest(text), 'draft_sha256': digest(draft), 'draft_reply': draft,
            'summary_readback': summary.read_text(encoding='utf-8').split(START)[0].rstrip(),
            'review_required': True, 'note': 'Source bytes matched; origin/meaning still require review. No delivery recorded.'}


def finalize(project, summary, review_input):
    text = summary.read_text(encoding='utf-8')
    if digest(text) != review_input.get('record_sha256'):
        raise ValueError('record changed after preview; prepare and review again')
    record = parse_record(text)
    if record is None:
        raise ValueError('prepare a canonical record first')
    sources = checked_sources(project, record['sources'], summary)
    state = materialize(record, sources)
    kind, target, _ = route_record(state)
    rendered, answer = render(record, state, kind, target, sources)
    if rendered != text:
        raise ValueError('generated views do not match the canonical record')
    draft = draft_for(record, state, kind, target)
    if review_input.get('draft_sha256') != digest(draft):
        raise ValueError('review must address the complete generated draft')
    semantic = deepcopy(review_input.get('semantic_review'))
    if not isinstance(semantic, dict):
        raise ValueError('caller must supply its actual semantic_review; it is never generated')
    semantic['reviewed_reply_sha256'] = digest(draft)
    handoff = {'kind': kind, 'semantic_review': semantic}
    if target:
        handoff['decision_id'] = target
    if kind == 'plan_transition':
        resolved = [row for row in state['decisions'] if row['status'] in RESOLVED]
        handoff['choice_basis'] = [{'decision_id': row['id'], 'choice': row.get('value') or row['subject']}
                                   for row in resolved]
        if not resolved:
            handoff['choice_basis'] = {'no_material_choice_reason': '仅有已确认且由原约束唯一限定做法的要求'}
        chosen = next((row for row in resolved if row['status'] in ('decided', 'delegated')), None)
        if chosen:
            handoff['approach_basis'] = {'decision_id': chosen['id'], 'source_quote': chosen['source']}
    graph = workflow.check_final_record({'project': str(project), 'summary': str(summary),
                                         'turn_id': record['turn']['id'], 'answer': answer},
                                        state.get('branch_history', []), decision_ids=[row['id'] for row in state['decisions']])
    verified = {}
    for group in ('decisions', 'confirmed_requirements'):
        for row in record['state'].get(group, []):
            if group == 'decisions' and row.get('status') not in RESOLVED:
                continue
            verified[row['id']] = {'source': excerpt(row['source_ref'], sources)}
            if group == 'confirmed_requirements':
                verified[row['id']]['constraint_source'] = excerpt(row['constraint_source_ref'], sources)
    errors = workflow.validate(state) + workflow.validate_discussion_final(
        state, draft, handoff, graph, verified_sources=verified)
    result = {'ok': not errors, 'errors': errors}
    if errors:
        workflow.add_error_diagnostics(result, state)
    else:
        result.update(draft_reply=draft, record_sha256=digest(text), delivery_recorded=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('inspect', 'prepare', 'finalize'))
    parser.add_argument('--project', required=True)
    parser.add_argument('--summary', required=True)
    parser.add_argument('--source', action='append', default=[])
    parser.add_argument('--request')
    parser.add_argument('--review')
    args = parser.parse_args()
    try:
        project = Path(args.project).resolve()
        summary = local_path(project, args.summary)
        if summary.suffix != '.md' or not summary.is_file():
            raise ValueError('use an existing authorized Markdown task summary')
        if args.mode == 'inspect':
            canonical = parse_record(summary.read_text(encoding='utf-8'))
            if canonical is not None:
                canonical = {key: value for key, value in canonical.items()
                             if key not in ('legacy_text', 'graph_template')}
            result = {'ok': True, 'record_sha256': digest(summary.read_bytes()),
                      'canonical': canonical,
                      'sources': [{'path': value, 'sha256': digest(local_path(project, value).read_bytes()),
                                   'lines': len(local_path(project, value).read_text(encoding='utf-8').splitlines())}
                                  for value in args.source]}
        elif args.mode == 'prepare':
            result = prepare(project, summary, load_json(local_path(project, args.request)))
        else:
            result = finalize(project, summary, load_json(local_path(project, args.review)))
    except (ValueError, KeyError, TypeError, OSError) as error:
        result = {'ok': False, 'errors': [str(error)]}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
