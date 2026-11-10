#!/usr/bin/env python3
"""Validate a task-driver checkpoint.

The caller owns semantic interpretation and must supply evidence references.
This script cannot establish that a reference supports a claimed decision.
"""
import sys
sys.dont_write_bytecode = True

import argparse
import json
import re

PHASES = {'analysis', 'discussion', 'planning', 'goals', 'execution', 'verification', 'review'}
STATUSES = {'continue', 'wait_user', 'wait_tool', 'blocked', 'paused', 'complete'}
GATES = ('plan', 'goals', 'execution', 'subagents')
INTERRUPTION_STATUSES = STATUSES | {'cancelled'}
GUIDANCE = {
    'present_incomplete_plan': '在正文交付标明缺口的讨论稿，不能称为正式计划或请求执行。',
    'verify_plan_request': '核对当前计划请求与已交付草案的实际对应关系，再更新状态；不要重复提问或编造交付。',
    'present_plan': '讨论闭合后在正文一起展示正式计划和目标；用户明确限制只展示其中一项时，说明严格流程并等待调整范围。展示不等于确认或执行授权，内容尚无有效确认时不提供执行选项；用户明确本轮不执行时不附执行选择。',
    'request_plan_transition': '总结有效决定，完成 semantic_review 后最后询问是否结束讨论并开始展示正式计划与目标；措辞可自然变化。',
    'resolve_pending': '处理尚有影响的事项：能调查先调查，委托范围内自行决定，其余讨论。讨论阶段最终回复必须始终以一个问题结束，完成 semantic_review 后再收口，不得仅汇报分析；不要重问已决事项。',
    'check_coverage': '先核对目标、已有资料、决定和未决事项，再以新状态检查；不得编造问题。',
    'continue_local': '先完成已获授权的独立或局部动作，不扩大用户限定的范围；原等待或受阻状态保持不变。',
    'local_complete': '交付局部结果并保留原任务恢复点。',
    'check_operation': '仅在查询权限内只读核实原操作及回执；不授权新操作或重试，结果未知时不得重复执行副作用动作。',
    'handle_operation_failure': '原操作已失败且阻塞下一步；先按审查模块分类，保留失败证据，不重复执行，不把局部任务标记完成。',
    'scope_complete': '本轮只交付用户明确限定的内容；交付后停止，保留整体任务恢复点，不追加问题或推进下一阶段。',
    'handle_interruption': '先处理当前临时请求，核对用户与宿主授权；业务执行仍须满足原有执行门槛，不扩大原任务授权。',
    'reconcile_interruption': '核对临时结果、恢复点、最新用户要求和实际现场；正文先交付临时结果，再接回对应事项。用户明确暂停时保持暂停。',
}

SEMANTIC_REVIEWERS = {'main', 'independent'}
DECISION_REVIEW_CHECKS = (
    'target_is_current',
    'not_already_decided',
    'not_delegated',
    'answerable_now',
    'single_question',
    'no_trailing_content',
)
TRANSITION_REVIEW_CHECKS = (
    'transition_intent',
    'no_blocking_pending_decisions',
    'single_question',
    'no_trailing_content',
)
WAIVER_REVIEW_CHECKS = (
    'waiver_source_is_explicit',
    'no_user_question',
    'no_trailing_content',
)


def make_resume_point(parent):
    keys = ('id', 'phase', 'status', 'next_action', 'wait_reason', 'wait_evidence')
    return {key: parent[key] for key in keys if key in parent}


def validate_interruptions(s):
    frames = s.get('interruptions', [])
    if not isinstance(frames, list):
        return ['interruptions must be a list']
    errors, ids = [], set()
    for frame in frames:
        if not isinstance(frame, dict):
            errors.append('interruption must be an object')
            continue
        for key in ('id', 'request', 'source', 'next_action'):
            value = frame.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append('interruption ' + key + ' required')
        ident = frame.get('id')
        if isinstance(ident, str) and ident in ids:
            errors.append('duplicate interruption id')
        if isinstance(ident, str):
            ids.add(ident)
        status = frame.get('status')
        if not isinstance(status, str) or status not in INTERRUPTION_STATUSES:
            errors.append('invalid interruption status')
        if 'allow_while_paused' in frame and not isinstance(frame['allow_while_paused'], bool):
            errors.append('interruption allow_while_paused must be boolean')
        if frame.get('allow_while_paused') is True and (not isinstance(frame.get('allow_while_paused_source'), str) or not frame['allow_while_paused_source'].strip()):
            errors.append('interruption while paused requires explicit request source')
        if status in ('wait_user', 'wait_tool', 'blocked', 'paused'):
            if not isinstance(frame.get('wait_reason'), str) or not frame['wait_reason'].strip():
                errors.append('interruption wait_reason required')
        if status == 'wait_user' and (not isinstance(frame.get('wait_evidence'), str) or not frame['wait_evidence'].strip()):
            errors.append('interruption wait_user requires presented question')
        if status in ('complete', 'cancelled') and (not isinstance(frame.get('result_evidence'), str) or not frame['result_evidence'].strip()):
            errors.append('interruption result_evidence required')
        point = frame.get('resume_point')
        if status in ('complete', 'cancelled') and point is None:
            errors.append('interruption resume_point required before reconciliation')
        if point is not None:
            if not isinstance(point, dict) or not isinstance(point.get('status'), str) or point['status'] not in INTERRUPTION_STATUSES or not isinstance(point.get('next_action'), str) or not point['next_action'].strip():
                errors.append('invalid interruption resume_point')
            elif not ((isinstance(point.get('phase'), str) and point['phase'] in PHASES) or (isinstance(point.get('id'), str) and point['id'].strip())):
                errors.append('resume_point requires original phase or interruption id')
            elif point['status'] in ('wait_user', 'wait_tool', 'blocked', 'paused') and (not isinstance(point.get('wait_reason'), str) or not point['wait_reason'].strip()):
                errors.append('resume_point wait_reason required')
            elif point['status'] == 'wait_user' and (not isinstance(point.get('wait_evidence'), str) or not point['wait_evidence'].strip()):
                errors.append('resume_point wait_user requires presented question')
    return errors



def validate(s):
    errors = []
    if not isinstance(s, dict):
        return ['checkpoint must be an object']
    errors.extend(validate_interruptions(s))
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
        if status in ('decided', 'delegated') and (not isinstance(item.get('value'), str) or not item['value'].strip()):
            errors.append(status + ' item requires its actual value')
        if status == 'pending' and (item.get('blocks_plan') is False or item.get('blocks_completion') is False):
            if not isinstance(item.get('nonblocking_reason'), str) or not item['nonblocking_reason'].strip():
                errors.append('nonblocking pending decision requires reason')
    plan = s.get('plan')
    if not isinstance(plan, dict) or not isinstance(plan.get('presented'), bool):
        errors.append('plan.presented must be true or false')
        plan = {}
    elif plan['presented'] and (not isinstance(plan.get('evidence'), str) or not plan['evidence'].strip()):
        errors.append('presented plan requires evidence')
    goals = s.get('goals')
    if goals is not None:
        if not isinstance(goals, dict) or not isinstance(goals.get('presented'), bool):
            errors.append('goals.presented must be true or false')
        elif goals['presented'] and (not isinstance(goals.get('evidence'), str) or not goals['evidence'].strip()):
            errors.append('presented goals require evidence')
        if isinstance(goals, dict) and goals.get('presented') is True and plan.get('presented') is not True:
            errors.append('goals cannot be presented without plan')
        if (isinstance(goals, dict) and goals.get('presented') is True and
                plan.get('presented') is True):
            plan_id = plan.get('presentation_id')
            goals_id = goals.get('presentation_id')
            if (not isinstance(plan_id, str) or not plan_id.strip() or
                    not isinstance(goals_id, str) or not goals_id.strip() or
                    plan_id != goals_id):
                errors.append('plan and goals require shared presentation_id')
        if isinstance(goals, dict):
            goal_status = goals.get('status')
            if goal_status not in (None, 'active', 'superseded'):
                errors.append('invalid goal status')
            elif goal_status == 'superseded':
                if (not isinstance(goals.get('source'), str) or not goals['source'].strip() or
                        not isinstance(goals.get('superseded_by'), str) or not goals['superseded_by'].strip()):
                    errors.append('superseded goals require source and superseded_by')
    superseded_goals = s.get('superseded_goals', [])
    if not isinstance(superseded_goals, list):
        errors.append('superseded_goals must be a list')
    else:
        for item in superseded_goals:
            if not isinstance(item, dict):
                errors.append('superseded goal must be an object')
                continue
            for key in ('objective', 'host_id', 'source', 'superseded_by'):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    errors.append('superseded goal ' + key + ' required')
    host_goal_sync = s.get('host_goal_sync')
    if host_goal_sync not in (None, 'synced', 'stale', 'unavailable'):
        errors.append('invalid host goal sync status')
    elif host_goal_sync in ('stale', 'unavailable') and not superseded_goals:
        errors.append('stale or unavailable host goal requires superseded_goals')
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
    if s.get('phase') == 'planning' and plan_required is False and plan.get('presented') is not True:
        errors.append('plan cannot be waived in planning stage')
    if (s.get('phase') == 'goals' or (plan_required is not False and s.get('phase') in ('execution', 'verification', 'review'))) and plan.get('presented') is not True:
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
    if phase in ('verification', 'review') and not isinstance(s.get('execution_occurred'), bool):
        errors.append('execution_occurred must be explicitly true or false')
    if s.get('status') in ('wait_user', 'wait_tool', 'blocked', 'paused'):
        reason = s.get('wait_reason')
        if not isinstance(reason, str) or not reason.strip():
            errors.append('wait_reason required')
    if s.get('status') == 'wait_user' and (not isinstance(s.get('wait_evidence'), str) or not s['wait_evidence'].strip()):
        errors.append('wait_user requires reference to already presented question')
    waiver = s.get('discussion_question_waiver_source')
    if waiver is not None and (not isinstance(waiver, str) or not waiver.strip()):
        errors.append('discussion question waiver requires source')
    scope_limited = s.get('scope_limited')
    if scope_limited is not None and not isinstance(scope_limited, bool):
        errors.append('scope_limited must be boolean')
    elif scope_limited is True:
        source = s.get('scope_limited_source')
        if not isinstance(source, str) or not source.strip():
            errors.append('scope limited source required')
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
    checking_operation = any(isinstance(op, dict) and op.get('blocks_next') is True and op.get('status') in ('unknown', 'running') for op in operations)
    independent_checks = any(isinstance(op, dict) and op.get('status') in ('unknown', 'running') and
                             op.get('independent_of_wait') is True for op in operations)
    querying_operation = (((checking_operation and s.get('status') == 'continue') or
                           (independent_checks and s.get('status') in ('wait_user', 'wait_tool'))) and not s.get('interruptions') and
                          not (s.get('local_only') is True and s.get('local_done') is True))
    needs_execution_gates = phase == 'execution' or (phase in ('verification', 'review') and s.get('execution_occurred') is not False)
    if needs_execution_gates:
        if plan_required is False and plan.get('presented') is not True:
            errors.append('plan must be presented before execution')
        if not isinstance(goals, dict) or goals.get('presented') is not True:
            errors.append('goals must be presented before execution')
        for name in GATES:
            if not gates.get(name) and not (name in ('execution', 'subagents') and querying_operation):
                errors.append(name + ' evidence required for execution or later')
    if phase == 'execution' and s.get('status') == 'continue' and not checking_operation and not (s.get('local_only') is True and s.get('local_done') is True):
        if s.get('coverage_checked') is not True:
            errors.append('discussion coverage must be checked before execution')
        if any(isinstance(item, dict) and item.get('status') == 'pending' and item.get('blocks_plan', True) is not False for item in items):
            errors.append('pending decisions prevent execution')
    if s.get('status') == 'complete':
        if any(isinstance(op, dict) and op.get('blocks_completion', True) is not False and
               op.get('status') in ('unknown', 'running', 'failed')
               for op in operations):
            errors.append('unresolved operation prevents completion')
        if plan_required is not False and plan.get('presented') is not True:
            errors.append('required plan must be presented before completion')
        if plan_required is not False and (not isinstance(goals, dict) or goals.get('presented') is not True):
            errors.append('required goals must be presented before completion')
        if isinstance(goals, dict) and goals.get('status') == 'superseded':
            errors.append('superseded goals cannot be used for completion')
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
    old_frames, new_frames = previous.get('interruptions', []), current.get('interruptions', [])
    if not isinstance(old_frames, list) or not isinstance(new_frames, list):
        errors.append('interruptions must be lists for comparison')
    elif validate_interruptions(previous) or validate_interruptions(current):
        errors.append('invalid interruption for comparison')
    else:
        old_ids = [frame['id'] for frame in old_frames]
        new_ids = [frame['id'] for frame in new_frames]
        common = min(len(old_ids), len(new_ids))
        if old_ids[:common] != new_ids[:common]:
            errors.append('interruption order changed or active request was replaced')
        if len(new_ids) < len(old_ids):
            if len(old_ids) - len(new_ids) != 1:
                errors.append('resume one interruption at a time')
            elif old_frames[-1]['status'] not in ('complete', 'cancelled'):
                errors.append('cannot resume before interruption completes or is cancelled')
        for old, new in zip(old_frames[:common], new_frames[:common]):
            if old['id'] != new['id']:
                continue
            if old['request'] != new['request'] and old['source'] == new['source']:
                errors.append('changed interruption request requires new source')
            if old.get('resume_point') is not None and old.get('resume_point') != new.get('resume_point'):
                errors.append('saved interruption resume_point cannot change')
            if old['status'] == 'paused' and new['status'] not in ('paused', 'cancelled'):
                if not isinstance(new.get('resume_source'), str) or not new['resume_source'].strip():
                    errors.append('resuming paused interruption requires source')
            if old['status'] in ('complete', 'cancelled') and new['status'] != old['status']:
                errors.append('completed interruption cannot change status')
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
    old_waiver = previous.get('discussion_question_waiver_source')
    new_waiver = current.get('discussion_question_waiver_source')
    left_local_only = previous.get('local_only') is True and current.get('local_only') is not True
    if (isinstance(old_waiver, str) and old_waiver.strip() and new_waiver == old_waiver and
            (previous.get('status') == 'paused' and current.get('status') != 'paused' or left_local_only)):
        errors.append('discussion question waiver cannot persist across resume')
    scope_state_changed = any(
        previous.get(key) != current.get(key)
        for key in ('status', 'next_action', 'decisions', 'plan', 'goals', 'operations')
    )
    if (previous.get('scope_limited') is True and current.get('scope_limited') is True and
            scope_state_changed and
            current.get('scope_limited_source') == previous.get('scope_limited_source')):
        errors.append('scope limited waiver cannot persist across resume')
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
        if old.get('status') not in ('decided', 'delegated', 'excluded'):
            continue
        item = new_items.get(ident)
        if item is None:
            changed = True
            source = removals.get(ident)
            if not isinstance(source, str) or not source.strip():
                errors.append('removed decision requires source')
        elif any(old.get(key) != item.get(key) for key in ('subject', 'value', 'status')):
            changed = True
            if item.get('status') != 'pending' and (not item.get('source') or item.get('source') == old.get('source')):
                review = current.get('impact_review')
                within_delegation = (old.get('status') == item.get('status') == 'delegated' and
                                     old.get('subject') == item.get('subject') and
                                     bool(item.get('source')) and
                                     isinstance(review, dict) and isinstance(review.get('reason'), str) and
                                     bool(review['reason'].strip()))
                if not within_delegation:
                    errors.append('changed decision requires new source')
    old_plan, new_plan = previous.get('plan'), current.get('plan')
    if isinstance(old_plan, dict) and isinstance(new_plan, dict) and old_plan.get('presented') is True and new_plan.get('presented') is True and old_plan.get('evidence') != new_plan.get('evidence'):
        changed = True
    old_goals, new_goals = previous.get('goals'), current.get('goals')
    if (isinstance(old_plan, dict) and old_plan.get('presented') is True and
            (not isinstance(old_goals, dict) or old_goals.get('presented') is not True) and
            isinstance(new_goals, dict) and new_goals.get('presented') is True):
        plan_id = new_plan.get('presentation_id') if isinstance(new_plan, dict) else None
        goals_id = new_goals.get('presentation_id')
        if (not isinstance(plan_id, str) or not plan_id.strip() or
                not isinstance(goals_id, str) or not goals_id.strip() or
                plan_id != goals_id):
            errors.append('plan and goals must be presented with a shared presentation_id')
    if isinstance(old_goals, dict) and isinstance(new_goals, dict) and old_goals.get('presented') is True and new_goals.get('presented') is True and old_goals.get('evidence') != new_goals.get('evidence'):
        changed = True
        old_gates, new_gates = previous.get('gates'), current.get('gates')
        if (isinstance(old_gates, dict) and isinstance(new_gates, dict) and
                (not new_gates.get('goals') or
                 old_gates.get('goals') == new_gates.get('goals'))):
            errors.append('changed goals require current goal confirmation source')
        if not current.get('superseded_goals') and current.get('host_goal_sync') not in ('stale', 'unavailable'):
            errors.append('changed goals require superseded_goals or stale host goal record')
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
    if isinstance(old_goals, dict) and old_goals.get('presented') is True and (not isinstance(new_goals, dict) or new_goals.get('presented') is not True):
        if isinstance(old_gates, dict) and isinstance(new_gates, dict):
            for name in ('goals', 'execution'):
                if old_gates.get(name) and old_gates.get(name) == new_gates.get(name):
                    errors.append('changed goals require reviewing old ' + name + ' authorization')
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
    frames = s.get('interruptions', []) if isinstance(s, dict) else []
    if isinstance(frames, list) and frames:
        frame_errors = validate_interruptions(s)
        if frame_errors:
            if s.get('status') == 'paused':
                return {'action': 'paused', 'reason': s.get('wait_reason'), 'errors': errors}
            return {'action': 'repair_state', 'errors': frame_errors}
        frame = frames[-1]
        if s.get('status') == 'paused' and frame['status'] == 'continue' and frame.get('allow_while_paused') is not True:
            return {'action': 'paused', 'reason': s.get('wait_reason'), 'errors': errors}
        result = {'interruption_id': frame['id']}
        if frame['status'] == 'continue':
            parent = frames[-2] if len(frames) > 1 else s
            result.update(action='handle_interruption', next_action=frame['next_action'],
                          resume_point=frame.get('resume_point', make_resume_point(parent)))
        elif frame['status'] in ('complete', 'cancelled'):
            result.update(action='reconcile_interruption', outcome=frame['status'],
                          result_evidence=frame['result_evidence'],
                          resume_to=frames[-2]['id'] if len(frames) > 1 else s.get('task_id'),
                          resume_point=frame['resume_point'])
        else:
            result.update(action='wait_interruption', status=frame['status'], reason=frame['wait_reason'])
        original_errors = validate(dict(s, interruptions=[]))
        if original_errors:
            result['original_state_errors'] = original_errors
        return result
    if isinstance(s, dict) and s.get('status') == 'paused':
        return {'action': 'paused', 'reason': s.get('wait_reason'), 'errors': errors}
    if errors:
        return {'action': 'repair_state', 'errors': errors}
    status = s['status']
    independent = s.get('independent_action')
    if status == 'blocked' and isinstance(independent, str) and independent.strip():
        return {'action': 'continue_local', 'next_action': independent, 'blocked_reason': s['wait_reason']}
    goals = s.get('goals')
    if (status == 'blocked' and s['phase'] in ('planning', 'goals') and
            s['plan'].get('presented') is True and
            (not isinstance(goals, dict) or goals.get('presented') is not True) and
            s.get('local_only') is not True):
        return {'action': 'continue_local',
                'next_action': '先核对计划确认、待决事项及当前展示范围；允许时一起展示计划和目标，否则处理缺口或等待。',
                'blocked_reason': s['wait_reason']}
    if status in ('wait_user', 'wait_tool'):
        for operation in s.get('operations', []):
            if (isinstance(operation, dict) and operation.get('blocks_next') is True and
                    operation.get('status') == 'failed'):
                return {'action': 'handle_operation_failure',
                        'reference': operation.get('reference')}
    if status != 'continue':
        result = {'action': status, 'reason': s.get('wait_reason')}
        if status in ('wait_user', 'wait_tool'):
            gates = s.get('gates', {})
            needs_execution_gates = (s['phase'] == 'execution' or
                                     (s['phase'] in ('verification', 'review') and s.get('execution_occurred') is not False))
            if s.get('independent_action') and (not needs_execution_gates or
                                                  (gates.get('execution') and gates.get('subagents'))):
                result['independent_action'] = s['independent_action']
            checks = [op.get('reference') for op in s.get('operations', []) if isinstance(op, dict) and op.get('status') in ('running', 'unknown') and op.get('independent_of_wait') is True]
            if checks:
                result['independent_checks'] = checks
        return result
    for operation in s.get('operations', []):
        if not isinstance(operation, dict) or operation.get('blocks_next') is not True:
            continue
        if operation.get('status') in ('unknown', 'running'):
            return {'action': 'check_operation', 'reference': operation.get('reference')}
        if operation.get('status') == 'failed':
            return {'action': 'handle_operation_failure', 'reference': operation.get('reference')}
    if s.get('local_only') and s.get('local_done'):
        if s.get('coverage_checked') is not True:
            return {'action': 'check_coverage'}
        return {'action': 'local_complete'}
    if s.get('local_only'):
        return {'action': 'continue_local', 'next_action': s['next_action']}
    if (s.get('scope_limited') is True and s.get('coverage_checked') is True and
            s.get('plan_requested') is not True and
            not (s.get('plan', {}).get('presented') is True and
                 (not isinstance(goals, dict) or goals.get('presented') is not True))):
        return {'action': 'scope_complete'}
    if s['phase'] in ('discussion', 'planning', 'goals'):
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
        if s['plan']['presented'] and (not isinstance(goals, dict) or goals.get('presented') is not True):
            return {'action': 'present_plan'}
        if s.get('plan_required', True) and not s['plan']['presented']:
            return {'action': 'present_plan' if s['plan_requested'] else 'request_plan_transition'}
    return {'action': 'continue_current_phase', 'next_action': s['next_action']}


def discussion_final_line(reply):
    lines = [line.strip() for line in reply.splitlines() if line.strip()]
    return lines[-1] if lines else ''


def validate_semantic_review(review, kind, decision_id=None, extra_checks=()):
    """Validate the semantic review contract; the review itself stays human/model-owned."""
    if not isinstance(review, dict):
        return ['discussion semantic review required']
    errors = []
    if review.get('reviewer') not in SEMANTIC_REVIEWERS:
        errors.append('discussion semantic review reviewer must be main or independent')
    elif review.get('reviewer') == 'independent':
        for key in ('review_id', 'authorization_source'):
            value = review.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append('discussion semantic review independent ' + key + ' required')
    if review.get('status') != 'pass':
        errors.append('discussion semantic review did not pass')
    source = review.get('source')
    if not isinstance(source, str) or not source.strip():
        errors.append('discussion semantic review requires source')
    if review.get('target') != kind:
        errors.append('discussion semantic review target must match handoff kind')
    if kind == 'decision' and review.get('decision_id') != decision_id:
        errors.append('discussion semantic review decision_id must match handoff')
    checks = review.get('checks')
    if not isinstance(checks, dict):
        errors.append('discussion semantic review checks must be an object')
        return errors
    required = {
        'decision': DECISION_REVIEW_CHECKS,
        'plan_transition': TRANSITION_REVIEW_CHECKS,
        'waived': WAIVER_REVIEW_CHECKS,
    }.get(kind, ())
    for name in tuple(required) + tuple(extra_checks):
        if checks.get(name) is not True:
            errors.append('discussion semantic review check failed: ' + name)
    return errors


def count_questions_outside_code(reply):
    """Count visible question marks as a structural heuristic, not a semantic judgment."""
    count = 0
    in_fence = False
    for line in reply.splitlines():
        stripped = line.strip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if re.match(r'^\s*\[[^\]]+\]:\s+\S*\?\S*', line):
            continue
        visible = re.sub(r'`[^`]*`|https?://\S+', '', line)
        visible = re.sub(r'\]\([^)]*\?[^)]*\)', ']', visible)
        visible = re.sub(r'“[^”\n]*[?？][^”\n]*”|"[^"\n]*[?？][^"\n]*"|「[^」\n]*[?？][^」\n]*」|『[^』\n]*[?？][^』\n]*』|‘[^’\n]*[?？][^’\n]*’|\'[^\'\n]*[?？][^\'\n]*\'', '', visible)
        visible = re.sub(r'(?<!\w)(?:https?://|www\.|/|\.\.?/)[^\s，。；！？]*\?[^\s，。；！？]*', '', visible)
        visible = re.sub(r'(?<!\w)(?:www\.)?[A-Za-z0-9][A-Za-z0-9._~:/#\[\]@!$&()*+,;=%-]*\?[A-Za-z0-9][A-Za-z0-9._~:/#\[\]@!$&()*+,;=%-]*', '', visible)
        count += visible.count('?') + visible.count('？')
    return count


def validate_discussion_final(s, reply, handoff):
    """Require a discussion handoff to end with one actionable question."""
    if not isinstance(s, dict) or s.get('phase') != 'discussion':
        return []
    if not isinstance(handoff, dict):
        return ['discussion final requires discussion_handoff']
    if not isinstance(reply, str) or not reply.strip():
        return ['discussion final reply required']
    blocking_operations = [
        operation.get('reference', operation.get('id', 'unknown'))
        for operation in s.get('operations', [])
        if isinstance(operation, dict)
        and operation.get('status') in ('running', 'unknown', 'failed')
        and operation.get('blocks_next') is True
    ]
    if blocking_operations:
        return ['discussion final blocked by unresolved operation: ' + ', '.join(blocking_operations)]
    kind = handoff.get('kind')
    if kind not in ('decision', 'plan_transition', 'waived'):
        return ['discussion_handoff.kind must be decision, plan_transition, or waived']
    question_count = count_questions_outside_code(reply)
    waiver = s.get('discussion_question_waiver_source')
    route_action = route(s).get('action')
    extra_review_checks = (
        ('incomplete_plan_delivered',)
        if (kind == 'decision' and s.get('plan_requested') is True and
            not (isinstance(s.get('plan'), dict) and s['plan'].get('presented') is True))
        else ()
    )
    review_errors = validate_semantic_review(
        handoff.get('semantic_review'), kind, handoff.get('decision_id'),
        extra_checks=extra_review_checks,
    )
    if kind == 'waived':
        if s.get('scope_limited') is True:
            source = s.get('scope_limited_source')
            if not isinstance(source, str) or not source.strip():
                return ['scope limited source required']
            if route_action not in ('scope_complete', 'local_complete', 'paused', 'complete'):
                return ['discussion final cannot bypass active interruption or blocking state with scoped stop']
            if question_count != 0:
                review_errors.append('scope limited discussion final must not add a question')
            return review_errors
        if not isinstance(waiver, str) or not waiver.strip():
            return ['discussion question waiver requires source']
        expected_action = None
        if s.get('status') == 'paused':
            expected_action = 'paused'
        elif s.get('status') == 'complete':
            expected_action = 'complete'
        elif s.get('local_only') is True and s.get('local_done') is True:
            if s.get('coverage_checked') is not True:
                return ['discussion final requires coverage_checked before handoff']
            expected_action = 'local_complete'
        if expected_action is None:
            return ['discussion question waiver only applies to pause, completed local-only turn, or completed task']
        if route_action != expected_action:
            review_errors.append('discussion question waiver conflicts with next action: ' + str(route_action))
        if question_count != 0:
            review_errors.append('discussion waiver final must not add a question')
        return review_errors
    if s.get('status') in ('paused', 'complete') or isinstance(waiver, str) and waiver.strip():
        return ['discussion final cannot bypass question while paused, complete, or waived; use handoff kind waived']

    line = discussion_final_line(reply)
    trimmed = line.rstrip('*_` \t')
    errors = list(review_errors)
    if count_questions_outside_code(reply) != 1 or not trimmed.endswith(('?', '？')):
        errors.append('discussion final reply must end with exactly one question')
    if s.get('coverage_checked') is not True:
        errors.append('discussion final requires coverage_checked before handoff')
    if route_action == 'present_incomplete_plan':
        plan = s.get('plan')
        if not isinstance(plan, dict) or plan.get('draft_presented') is not True:
            errors.append('discussion final must deliver the incomplete plan draft')
        elif plan.get('draft_for_request') != s.get('plan_request_source'):
            errors.append('discussion final must tie the incomplete plan draft to the current request')

    pending = [item for item in s.get('decisions', [])
               if isinstance(item, dict) and item.get('status') == 'pending'
               and item.get('blocks_plan', True) is not False]
    if kind == 'decision':
        if not pending:
            errors.append('discussion decision handoff requires a blocking pending decision')
        if route_action not in ('resolve_pending', 'present_incomplete_plan', 'wait_user', 'wait_tool', 'blocked'):
            errors.append('discussion decision handoff conflicts with next action: ' + str(route_action))
        decision_id = handoff.get('decision_id')
        decision = next((item for item in pending if item.get('id') == decision_id), None)
        if decision is None:
            errors.append('discussion decision handoff requires a matching pending decision_id')
        else:
            expected_question = decision.get('question')
            if not isinstance(expected_question, str) or not expected_question.strip():
                errors.append('discussion decision handoff requires the pending decision question')
    elif kind == 'plan_transition':
        if pending:
            errors.append('discussion plan transition cannot bypass pending decisions')
        if route_action != 'request_plan_transition':
            errors.append('discussion plan transition conflicts with next action: ' + str(route_action))
        if isinstance(s.get('plan'), dict) and s['plan'].get('presented') is True:
            errors.append('discussion plan transition cannot be used after the formal plan is already presented')
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('check', 'next', 'final'))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--state')
    source.add_argument('--json', dest='inline_json')
    args = parser.parse_args()
    try:
        if args.inline_json is not None:
            payload = json.loads(args.inline_json)
        elif args.state == '-':
            payload = json.load(sys.stdin)
        else:
            with open(args.state, encoding='utf-8') as f:
                payload = json.load(f)

        if args.mode == 'final':
            if not isinstance(payload, dict) or not isinstance(payload.get('state'), dict):
                raise ValueError('final requires {"state":{...},"draft_reply":"..."}')
            state = payload['state']
            draft_reply = payload.get('draft_reply')
            if not isinstance(draft_reply, str):
                raise ValueError('final requires a string draft_reply')
            discussion_handoff = payload.get('discussion_handoff')
            previous = payload.get('previous')
        else:
            state = payload
            draft_reply = None
            discussion_handoff = None
            previous = state.get('previous') if isinstance(state, dict) and 'state' in state and 'previous' in state else None
        if previous is not None:
            if args.mode != 'final':
                state = state['state']
        errors = validate(state)
        transition_errors = []
        if previous is not None:
            transition_errors = validate_transition(previous, state)
            errors.extend(transition_errors)
        if args.mode == 'final':
            errors.extend(validate_discussion_final(state, draft_reply, discussion_handoff))
            result = {'ok': not errors, 'errors': errors}
        elif args.mode == 'next':
            result = route(state)
        else:
            result = {'ok': not errors, 'errors': errors}
        if previous is not None and transition_errors and isinstance(state, dict):
            is_paused = result.get('action') == 'paused' or (result.get('action') == 'wait_interruption' and result.get('status') == 'paused')
            if args.mode == 'next' and is_paused:
                result['errors'] = errors
            else:
                result = {'action': 'repair_state', 'errors': errors} if args.mode == 'next' else {'ok': False, 'errors': errors}
        if result.get('action') in GUIDANCE:
            result['instruction'] = GUIDANCE[result['action']]
        if args.mode == 'final':
            result['scope'] = 'structure_and_changes_and_reply' if previous is not None else 'structure_and_reply'
        else:
            result['scope'] = 'structure_and_changes' if previous is not None else 'structure_only'
        print(json.dumps(result, ensure_ascii=False))
        safe_actions = ('paused', 'handle_interruption', 'wait_interruption', 'reconcile_interruption')
        return bool(errors) and result.get('action') not in safe_actions
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({'ok': False, 'errors': [str(exc)]}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
