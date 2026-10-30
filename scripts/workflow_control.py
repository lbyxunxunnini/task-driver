#!/usr/bin/env python3
"""Validate a task-driver checkpoint.

The caller owns semantic interpretation and must supply evidence references.
This script cannot establish that a reference supports a claimed decision.
"""
import sys
sys.dont_write_bytecode = True

import argparse
import json

PHASES = {'analysis', 'discussion', 'planning', 'goals', 'execution', 'verification', 'review'}
STATUSES = {'continue', 'wait_user', 'wait_tool', 'blocked', 'paused', 'complete'}
GATES = ('plan', 'goals', 'execution')
GUIDANCE = {
    'present_incomplete_plan': '在正文交付标明缺口的讨论稿，不能称为正式计划或请求执行。',
    'verify_plan_request': '核对当前计划请求与已交付草案的实际对应关系，再更新状态；不要重复提问或编造交付。',
    'present_plan': '在正文实际列出正式计划；计划展示不等于确认或执行授权。计划或目标尚无有效确认时，不提供执行选项；用户明确本轮不执行时交付其要求的计划或目标及缺口，不附执行选择。',
    'request_plan_transition': '总结有效决定，请用户确认结束讨论并生成计划。',
    'resolve_pending': '处理尚有影响的事项：能调查先调查，委托范围内自行决定，其余讨论；不要重问已决事项。',
    'check_coverage': '先核对目标、已有资料、决定和未决事项，再以新状态检查；不得编造问题。',
    'continue_local': '先完成用户限定的局部动作，本轮不扩大范围。',
    'local_complete': '交付局部结果并保留原任务恢复点。',
    'check_operation': '先核实原操作及回执，结果未知时不得重复执行副作用动作。',
}



def validate(s):
    errors = []
    if not isinstance(s, dict):
        return ['checkpoint must be an object']
    if not isinstance(s.get('task_id'), str) or not s['task_id'].strip():
        errors.append('task_id required')
    if not isinstance(s.get('phase'), str) or s['phase'] not in PHASES:
        errors.append('invalid phase')
    if not isinstance(s.get('status'), str) or s['status'] not in STATUSES:
        errors.append('invalid status')
    if not isinstance(s.get('next_action'), str) or not s['next_action'].strip():
        errors.append('next_action required')
    items = s.get('decisions')
    if not isinstance(items, list):
        errors.append('decisions must be a list')
        items = []
    ids = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append('decision must be an object')
            continue
        ident, status = item.get('id'), item.get('status')
        if not isinstance(ident, str) or not ident.strip() or ident in ids:
            errors.append('decision id missing or duplicated')
        else:
            ids.add(ident)
        if status not in ('pending', 'decided', 'delegated', 'excluded'):
            errors.append('invalid decision status')
        if not isinstance(item.get('subject'), str) or not item['subject'].strip():
            errors.append('decision subject required')
        if status != 'pending' and (not isinstance(item.get('source'), str) or not item['source'].strip()):
            errors.append('resolved decision requires source')
        if status == 'decided' and (not isinstance(item.get('value'), str) or not item['value'].strip()):
            errors.append('decided item requires its actual value')
        if status == 'pending' and (item.get('blocks_plan') is False or item.get('blocks_completion') is False):
            if not isinstance(item.get('nonblocking_reason'), str) or not item['nonblocking_reason'].strip():
                errors.append('nonblocking pending decision requires reason')
    plan = s.get('plan')
    if not isinstance(plan, dict) or not isinstance(plan.get('presented'), bool):
        errors.append('plan.presented must be true or false')
        plan = {}
    elif plan['presented'] and (not isinstance(plan.get('evidence'), str) or not plan['evidence'].strip()):
        errors.append('presented plan requires evidence')
    if 'draft_presented' in plan and not isinstance(plan['draft_presented'], bool):
        errors.append('plan.draft_presented must be true or false')
    elif plan.get('draft_presented') is True and (not isinstance(plan.get('draft_evidence'), str) or not plan['draft_evidence'].strip()):
        errors.append('presented draft requires evidence')
    for key in ('draft_for_request', 'draft_not_for_request'):
        if key in plan:
            if not isinstance(plan[key], str) or not plan[key].strip():
                errors.append(key + ' must be a nonempty reference')
            elif plan.get('draft_presented') is not True:
                errors.append(key + ' requires presented draft')
    if plan.get('draft_for_request') and plan.get('draft_for_request') == plan.get('draft_not_for_request'):
        errors.append('draft request references conflict')
    plan_required = s.get('plan_required', True)
    if not isinstance(plan_required, bool):
        errors.append('plan_required must be true or false')
    elif not plan_required and (not isinstance(s.get('plan_waiver_source'), str) or not s['plan_waiver_source'].strip()):
        errors.append('plan waiver requires source')
    if plan_required is not False and s.get('phase') in ('goals', 'execution', 'verification', 'review') and plan.get('presented') is not True:
        errors.append('plan must be presented before goals or execution')
    if not isinstance(s.get('coverage_checked'), bool):
        errors.append('coverage_checked must be true or false')
    if not isinstance(s.get('plan_requested'), bool):
        errors.append('plan_requested must be true or false')
    elif s['plan_requested']:
        if plan_required is False:
            errors.append('active plan request conflicts with waiver')
        if not isinstance(s.get('plan_request_source'), str) or not s['plan_request_source'].strip():
            errors.append('active plan request requires source')
    for key in ('local_only', 'local_done'):
        if key in s and not isinstance(s[key], bool):
            errors.append(key + ' must be true or false')
    gates = s.get('gates')
    if not isinstance(gates, dict):
        errors.append('gates must be an object')
        gates = {}
    for name in GATES:
        value = gates.get(name)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            errors.append(name + ' evidence must be a nonempty reference or null')
    phase = s.get('phase')
    combined = s.get('combined_view_source')
    if phase == 'goals' and plan_required is not False and not gates.get('plan'):
        if not isinstance(combined, str) or not combined.strip():
            errors.append('goals require confirmed plan or combined-view source')
    if phase in ('verification', 'review') and not isinstance(s.get('execution_occurred'), bool):
        errors.append('execution_occurred must be explicitly true or false')
    needs_execution_gates = phase == 'execution' or (phase in ('verification', 'review') and s.get('execution_occurred') is not False)
    if needs_execution_gates:
        for name in GATES:
            if not gates.get(name):
                errors.append(name + ' evidence required for execution or later')
    if s.get('status') in ('wait_user', 'wait_tool', 'blocked', 'paused'):
        reason = s.get('wait_reason')
        if not isinstance(reason, str) or not reason.strip():
            errors.append('wait_reason required')
    if s.get('status') == 'wait_user' and (not isinstance(s.get('wait_evidence'), str) or not s['wait_evidence'].strip()):
        errors.append('wait_user requires reference to already presented question')
    operations = s.get('operations', [])
    if not isinstance(operations, list):
        errors.append('operations must be a list')
        operations = []
    operation_ids, operation_refs = set(), set()
    for op in operations:
        if not isinstance(op, dict):
            errors.append('operation must be an object')
            continue
        for key, used in (('id', operation_ids), ('reference', operation_refs)):
            value = op.get(key)
            if not isinstance(value, str) or not value.strip() or value in used:
                errors.append('operation ' + key + ' missing or duplicated')
            else:
                used.add(value)
        if op.get('status') not in ('running', 'unknown', 'failed', 'succeeded'):
            errors.append('invalid operation status')
        for key in ('side_effect', 'blocks_next'):
            if not isinstance(op.get(key), bool):
                errors.append('operation ' + key + ' must be boolean')
        for key in ('blocks_completion', 'independent_of_wait'):
            if key in op and not isinstance(op[key], bool):
                errors.append('operation ' + key + ' must be boolean')
        if op.get('status') in ('failed', 'succeeded') and (not isinstance(op.get('evidence'), str) or not op['evidence'].strip()):
            errors.append('operation result requires evidence')
        if op.get('status') in ('running', 'unknown') and op.get('blocks_completion') is False and (not isinstance(op.get('completion_unblock_reason'), str) or not op['completion_unblock_reason'].strip()):
            errors.append('nonblocking operation requires reason')
    if s.get('status') == 'complete':
        if any(isinstance(op, dict) and op.get('blocks_completion', True) is not False and op.get('side_effect') is True and op.get('status') in ('unknown', 'running') for op in operations):
            errors.append('unresolved side-effect operation prevents completion')
        if plan_required is not False and plan.get('presented') is not True:
            errors.append('required plan must be presented before completion')
        if plan_required is not False and s.get('phase') in ('discussion', 'planning') and s.get('coverage_checked') is not True:
            errors.append('coverage check required before completion')
        if any(i.get('status') == 'pending' and i.get('blocks_completion', True) is not False for i in items if isinstance(i, dict)):
            errors.append('pending decisions prevent completion')
        if not isinstance(s.get('completion_evidence'), str) or not s['completion_evidence'].strip():
            errors.append('completion evidence required')
    return errors


def validate_transition(previous, current):
    """Check explicit changes when both snapshots are available; never infer intent."""
    if not isinstance(previous, dict) or not isinstance(current, dict):
        return ['previous and current states must be objects']
    errors = []
    if previous.get('task_id') != current.get('task_id'):
        errors.append('task id changed')
    old_plan, new_plan = previous.get('plan'), current.get('plan')
    delivered = (isinstance(new_plan, dict) and new_plan.get('presented') is True and
                 (not isinstance(old_plan, dict) or old_plan.get('presented') is not True or
                  old_plan.get('evidence') != new_plan.get('evidence')))
    delivery_source = current.get('plan_request_delivery_source')
    if isinstance(delivery_source, str) and delivery_source.strip() and isinstance(new_plan, dict) and new_plan.get('presented') is True:
        delivered = True
    if previous.get('plan_requested') is True and current.get('plan_requested') is False and not delivered:
        source = current.get('plan_request_change_source')
        if not isinstance(source, str) or not source.strip():
            errors.append('withdrawing plan request requires source')
    if previous.get('status') == 'paused' and current.get('status') != 'paused':
        source = current.get('resume_source')
        if not isinstance(source, str) or not source.strip():
            errors.append('resuming paused task requires source')
    old_decisions = previous.get('decisions', [])
    new_decisions = current.get('decisions', [])
    if not isinstance(old_decisions, list) or not isinstance(new_decisions, list):
        return errors + ['decisions must be lists for comparison']
    old_items = {item.get('id'): item for item in old_decisions
                 if isinstance(item, dict) and isinstance(item.get('id'), str)}
    new_items = {item.get('id'): item for item in new_decisions
                 if isinstance(item, dict) and isinstance(item.get('id'), str)}
    changed = False
    removals = current.get('removed_decisions', {})
    if not isinstance(removals, dict):
        return errors + ['removed decisions must be an object']
    for ident, old in old_items.items():
        if old.get('status') != 'decided':
            continue
        item = new_items.get(ident)
        if item is None:
            changed = True
            source = removals.get(ident)
            if not isinstance(source, str) or not source.strip():
                errors.append('removed decision requires source')
        elif (old.get('value'), old.get('status')) != (item.get('value'), item.get('status')):
            changed = True
            if item.get('status') != 'pending' and (not item.get('source') or item.get('source') == old.get('source')):
                errors.append('changed decision requires new source')
    old_plan, new_plan = previous.get('plan'), current.get('plan')
    if isinstance(old_plan, dict) and isinstance(new_plan, dict) and old_plan.get('presented') is True and new_plan.get('presented') is True and old_plan.get('evidence') != new_plan.get('evidence'):
        changed = True
    old_gates, new_gates = previous.get('gates'), current.get('gates')
    if changed and isinstance(old_gates, dict) and isinstance(new_gates, dict):
        retained = {name for name in GATES if old_gates.get(name) and old_gates.get(name) == new_gates.get(name)}
        if retained:
            review = current.get('impact_review')
            if not isinstance(review, dict) or not isinstance(review.get('reason'), str) or not review['reason'].strip() or not isinstance(review.get('retained'), list) or not all(isinstance(name, str) for name in review['retained']) or not retained.issubset(set(review['retained'])):
                errors.append('changed scope requires reviewing retained authorizations')
    if isinstance(old_plan, dict) and isinstance(new_plan, dict) and old_plan.get('presented') is True and new_plan.get('presented') is False:
        old_gates, new_gates = previous.get('gates'), current.get('gates')
        if isinstance(old_gates, dict) and isinstance(new_gates, dict):
            for name in ('plan', 'execution'):
                if old_gates.get(name) and old_gates.get(name) == new_gates.get(name):
                    errors.append('changed plan requires reviewing old ' + name + ' authorization')
    return errors


def pending_plan_request_action(s):
    """Distinguish a delivered draft for this request from an older draft."""
    if not s['plan_requested'] or s['plan']['presented']:
        return None
    plan = s['plan']
    if not plan.get('draft_presented', False):
        return 'present_incomplete_plan'
    request = s['plan_request_source']
    if plan.get('draft_for_request') == request:
        return None
    if plan.get('draft_not_for_request') == request:
        return 'present_incomplete_plan'
    return 'verify_plan_request'


def route(s):
    """Return the next required category based on supplied facts, not model prose."""
    errors = validate(s)
    if isinstance(s, dict) and s.get('status') == 'paused':
        return {'action': 'paused', 'reason': s.get('wait_reason'), 'errors': errors}
    if errors:
        return {'action': 'repair_state', 'errors': errors}
    status = s['status']
    if status != 'continue':
        result = {'action': status, 'reason': s.get('wait_reason')}
        if status in ('wait_user', 'wait_tool'):
            if s.get('independent_action'):
                result['independent_action'] = s['independent_action']
            checks = [op.get('reference') for op in s.get('operations', []) if isinstance(op, dict) and op.get('status') in ('running', 'unknown') and op.get('side_effect') is True and op.get('independent_of_wait') is True]
            if checks:
                result['independent_checks'] = checks
        return result
    if s.get('local_only') and s.get('local_done'):
        return {'action': 'local_complete'}
    for operation in s.get('operations', []):
        if isinstance(operation, dict) and operation.get('blocks_next') is True and operation.get('side_effect') is True and operation.get('status') in ('unknown', 'running'):
            return {'action': 'check_operation', 'reference': operation.get('reference')}
    if s.get('local_only'):
        return {'action': 'continue_local', 'next_action': s['next_action']}
    if s['phase'] in ('discussion', 'planning'):
        if not s['coverage_checked']:
            action = pending_plan_request_action(s)
            if action:
                return {'action': action}
            return {'action': 'check_coverage'}
        if any(i.get('status') == 'pending' and i.get('blocks_plan', True) is not False for i in s['decisions']):
            action = pending_plan_request_action(s)
            if action:
                return {'action': action}
            return {'action': 'resolve_pending', 'next_action': s['next_action']}
        if s.get('plan_required', True) and not s['plan']['presented']:
            return {'action': 'present_plan' if s['plan_requested'] else 'request_plan_transition'}
    return {'action': 'continue_current_phase', 'next_action': s['next_action']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('check', 'next'))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--state')
    source.add_argument('--json', dest='inline_json')
    args = parser.parse_args()
    try:
        if args.inline_json is not None:
            state = json.loads(args.inline_json)
        elif args.state == '-':
            state = json.load(sys.stdin)
        else:
            with open(args.state, encoding='utf-8') as f:
                state = json.load(f)
        previous = state.get('previous') if isinstance(state, dict) and 'state' in state and 'previous' in state else None
        if previous is not None:
            state = state['state']
        errors = validate(state)
        if previous is not None:
            errors.extend(validate_transition(previous, state))
        result = route(state) if args.mode == 'next' else {'ok': not errors, 'errors': errors}
        if previous is not None and errors and isinstance(state, dict) and state.get('status') != 'paused':
            result = {'action': 'repair_state', 'errors': errors} if args.mode == 'next' else {'ok': False, 'errors': errors}
        if result.get('action') in GUIDANCE:
            result['instruction'] = GUIDANCE[result['action']]
        result['scope'] = 'structure_and_changes' if previous is not None else 'structure_only'
        print(json.dumps(result, ensure_ascii=False))
        return bool(errors) and result.get('action') != 'paused'
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({'ok': False, 'errors': [str(exc)]}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
