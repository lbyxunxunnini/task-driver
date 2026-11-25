#!/usr/bin/env python3
"""Validate a task-driver checkpoint.

The caller owns semantic interpretation and must supply evidence references.
This script cannot establish that a reference supports a claimed decision.
"""
import sys
sys.dont_write_bytecode = True

import argparse
from copy import deepcopy
import hashlib
import json
import re
from pathlib import Path

PHASES = {'analysis', 'discussion', 'planning', 'goals', 'execution', 'verification', 'review'}
STATUSES = {'continue', 'wait_user', 'wait_tool', 'blocked', 'paused', 'complete'}
GATES = ('plan', 'goals', 'execution', 'subagents')
INTERRUPTION_STATUSES = STATUSES | {'cancelled'}
GOAL_KINDS = {'changed', 'associated'}
EVIDENCE_KINDS = ('tool', 'artifact', 'user')
EVIDENCE_FIELDS = ('source', 'subject', 'observed')
COMPLETION_BASES = {'evidence', 'user_requested'}
GOAL_TRACKING_MODES = {'host', 'plan', 'conversation', 'unavailable'}
GOAL_TRACKING_FALLBACK_MODES = {'plan', 'conversation'}
STEP_STATUSES = {'pending', 'in_progress', 'done', 'blocked'}
GUIDANCE = {
    'present_incomplete_plan': (
        '必须先读取或复用本 skill 的 references/planning.md、references/goals.md 及 references/templates.md 的目标草案章节，'
        '再在正文交付标明缺口的讨论稿。禁止将讨论稿称为正式计划或请求执行。'
    ),
    'verify_plan_request': '必须先核对当前计划请求与已交付草案的实际对应关系，再更新状态。禁止重复提问或编造交付。',
    'present_plan': (
        '用户明确限制只展示其中一项时，禁止单独展示，必须说明同轮展示要求并等待用户调整范围。'
        '首次正式展示前，必须核实用户已对实际发出的收口问题明确作出肯定答复。'
        '必须先读取或复用本 skill 的 references/planning.md、references/goals.md 及 references/templates.md 的目标草案章节，'
        '按方法核对正文和状态，并调用 final 检查实际正文及 plan_coverage。符合展示条件时必须一起展示正式计划和目标，二者同轮送达。'
        '展示不等于确认或执行授权。内容尚无有效确认时，禁止提供执行选项。'
        '用户明确本轮不执行时，必须将确认限定在尚缺的计划或目标内容。禁止问“是否按计划执行”或承诺“确认后就开始”。'
        '开始执行前，必须另行取得用户对已展示内容的明确执行授权。用户后续明确授权时，必须沿用有效确认继续，禁止重复询问。'
    ),
    'request_plan_transition': (
        '调查分析完成且没有待决项时，必须保持讨论阶段，先更新并读回当前任务摘要，当前位置为等待用户同意。逐条说明已确认要求怎么做、怎么验。完成 semantic_review 后，'
        '必须以一个实际发出的收口问题结束回复，询问用户是否结束讨论并开始展示正式计划与验收目标。'
        '发出问题后必须等待用户答复。进入计划阶段前，必须取得用户针对该问题的明确肯定答复。'
        '即使用户已经给出完整方案、要求直接执行或要求展示计划，也必须完成这次收口问答。'
    ),
    'resolve_pending': (
        '处理仍有影响的待决项时，必须先调查可查事实，在委托范围内自行决定，其余与用户讨论。'
        '调查或决策改变待决状态时，必须按实际新状态重新调用 next。'
        '仍有必须由用户决定的待决项时，必须完成 semantic_review，并以一个当前的具体问题结束最终回复。'
        '待决项消除后必须按新路由处理收口或适用的免问情况。收到答复后必须重新核对剩余待决项。'
        '禁止重问已决事项、编造问题或在仍有待决项时请求结束讨论。'
    ),
    'check_coverage': '必须先核对目标、已有资料、决定和未决事项，再以新状态检查。禁止编造问题。',
    'continue_local': '必须先完成已获授权的独立或局部动作，并保持原等待或受阻状态。禁止扩大用户限定的范围。',
    'local_complete': '必须交付局部结果并保留原任务恢复点。',
    'check_operation': (
        '必须在查询权限内只读核实原操作及回执。禁止将查询权限用于新操作或重试。结果未知时禁止重复执行有副作用的动作。'
    ),
    'handle_operation_failure': '原操作已失败且阻塞下一步。必须先按审查模块分类并保留失败证据。禁止重复执行或将局部任务标记为完成。',
    'scope_complete': '必须将本轮交付限定在用户明确指定的内容内。交付后必须停止并保留整体任务恢复点。禁止追加问题或推进下一阶段。',
    'complete': (
        '完成前必须逐项检查 goals.included，核对 evidence_map 中的实际来源、当前产物或运行及观察结果是否覆盖各自的通过条件。'
        '禁止将 excluded 计入完成。证据不足时必须保持未完成。'
    ),
    'repair_state': (
        '必须修正状态结构。旧目标必须补录 included、excluded、evidence_map 和 goal_scope_baseline 后再继续。'
        '若用户明确要求结束或完成但仍有未验证项，必须先设置 completion_basis:user_requested，记录用户来源、completion_report 和 unverified_goals，再重试。'
        '禁止将用户结束要求视为验收或宣称未验证项已经验证。'
    ),
    'handle_interruption': '必须优先处理当前临时请求，处理前必须核对用户与宿主授权。业务执行仍必须满足原有执行门槛。禁止扩大原任务授权。',
    'ask_return_to_main': '先交付临时结果，再单独询问返回问题，发出后等待明示。',
    'reconcile_interruption': '必须核对临时结果、恢复点、最新用户要求和实际现场，正文必须先交付临时结果，再接回对应事项。用户明确暂停时必须保持暂停。',
    'begin_execution': (
        '执行入口尚未通过。必须核对分析闭合、讨论闭合、编号步骤、计划与目标确认、执行授权、子代理设置和目标跟踪回执。'
        '开始业务动作前必须运行 begin 并取得 execution_receipt。'
    ),
    'start_step': '必须从当前编号步骤开始。标记该步骤完成前，必须取得实际结果和证据。禁止提前开始或勾选后续步骤。',
    'continue_step': '必须继续当前进行中的编号步骤。进入下一步前必须完成该步骤并核对证据。',
    'step_blocked': '当前步骤受阻。必须先说明已完成部分、失败原因和是否影响后续步骤。禁止跳过该步骤。',
    'steps_complete': '所有编号步骤已完成。必须进入验证与审查，禁止继续做未列入计划的新业务动作。',
    'continue_analysis': '当前仍在分析阶段。必须将当前动作限定在补充事实、核对范围和进入讨论。禁止执行任何业务写入。',
}
USER_REQUESTED_COMPLETION_GUIDANCE = (
    '用户明确要求完成，必须按要求将业务标记完成，在 unverified_goals 和正文中逐项说明未验证目标、原因和影响，并记录 completion_request_source。'
    '禁止写成所有目标已验证。'
)

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
TOOL_WAIT_REVIEW_CHECKS = (
    'tool_wait_is_current',
    'no_blocking_pending_decisions',
    'no_user_question',
)


def make_resume_point(parent):
    keys = ('id', 'phase', 'status', 'next_action', 'wait_reason', 'wait_evidence')
    return {key: parent[key] for key in keys if key in parent}


def branch_errors(branch):
    if not isinstance(branch, dict) or branch.get('relation') not in ('related', 'unrelated'):
        return ['branch requires a related or unrelated relation']
    fields = ['origin']
    if branch['relation'] == 'related':
        fields.extend(('target', 'impact'))
    elif 'target' in branch or 'impact' in branch:
        return ['unrelated branch cannot have a merge target or impact']
    return ['branch requires ' + key for key in fields
            if not isinstance(branch.get(key), str) or not branch[key].strip()]


def unrelated_closed(frame):
    return (frame.get('status') in ('complete', 'cancelled') and
            frame.get('branch', {}).get('relation') == 'unrelated')


def has_return_consent(frame):
    return (frame.get('return_answer') == 'yes' or
            isinstance(frame.get('return_instruction_source'), str)
            and bool(frame['return_instruction_source'].strip())
            and frame.get('return_answer') is None)


def branch_record(frame):
    record = {**frame['branch'], 'id': frame['id'], 'request': frame['request']}
    if 'branch_revision_source' in frame:
        record['branch_revision_source'] = frame['branch_revision_source']
    return record


def validate_interruptions(s):
    frames = s.get('interruptions', [])
    if not isinstance(frames, list):
        return ['interruptions must be a list']
    errors, ids = [], set()
    history = s.get('branch_history', [])
    if not isinstance(history, list):
        return ['branch_history must be a list']
    for entry in history:
        errors.extend(branch_errors(entry))
        if not isinstance(entry, dict) or not all(isinstance(entry.get(k), str) and entry[k].strip()
                                                  for k in ('id', 'request')):
            errors.append('branch history requires id and request')
        elif entry['id'] in ids:
            errors.append('duplicate branch history id')
        else:
            ids.add(entry['id'])
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
        if 'branch' in frame:
            issues = branch_errors(frame['branch'])
            errors.extend(issues)
            if issues:
                continue
        for source_key in ('branch_revision_source', 'return_instruction_source'):
            if source_key in frame and (not isinstance(frame[source_key], str) or not frame[source_key].strip()):
                errors.append(source_key + ' requires a nonempty source')
        if 'return_instruction_source' in frame:
            if (frame.get('branch', {}).get('relation') != 'unrelated' or
                    any(key in frame for key in ('return_question_source', 'return_answer', 'return_answer_source'))):
                errors.append('return instruction requires an unrelated branch and replaces return question/answer fields')
        question = frame.get('return_question_source')
        answer = frame.get('return_answer')
        if any(k in frame for k in ('return_question_source', 'return_answer', 'return_answer_source')):
            if not unrelated_closed(frame) or not isinstance(question, str) or not question.strip():
                errors.append('return confirmation requires a closed unrelated branch and presented question')
            if 'return_answer' in frame or 'return_answer_source' in frame:
                if answer not in ('yes', 'no') or not has_new_source(frame.get('return_answer_source'), question):
                    errors.append('return answer requires an explicit user response source')
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


def evidence_record_errors(record):
    if not isinstance(record, dict):
        return ['must be a record']
    errors = []
    if record.get('kind') not in EVIDENCE_KINDS:
        errors.append('kind must be tool, artifact, or user')
    for field in EVIDENCE_FIELDS:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(field + ' required')
    return errors


def has_goal_evidence(records):
    return isinstance(records, list) and any(not evidence_record_errors(record) for record in records)


def validate_goal_scope(goals, require_completion_evidence=False, allow_empty_included=False):
    """Validate the goal scope and verify every included goal has evidence before completion."""
    errors = []
    included = goals.get('included')
    excluded = goals.get('excluded')
    evidence_map = goals.get('evidence_map')
    if not isinstance(included, list):
        errors.append('goals.included must be a list')
        included = []
    elif not included and not allow_empty_included:
        errors.append('goals.included must contain at least one item')
    if not isinstance(excluded, list):
        errors.append('goals.excluded must be a list')
        excluded = []
    if not isinstance(evidence_map, dict):
        errors.append('goals.evidence_map must be an object')
        evidence_map = {}

    included_ids, all_ids = set(), set()
    for index, item in enumerate(included):
        label = 'goals.included[' + str(index) + ']'
        if not isinstance(item, dict):
            errors.append(label + ' must be an object')
            continue
        ident = item.get('id')
        if not isinstance(ident, str) or not ident.strip() or ident in all_ids:
            errors.append(label + ' id missing or duplicated')
        else:
            included_ids.add(ident)
            all_ids.add(ident)
        if not isinstance(item.get('kind'), str) or item.get('kind') not in GOAL_KINDS:
            errors.append(label + ' kind must be changed or associated')
        for key in ('criterion', 'source'):
            value = item.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(label + ' ' + key + ' required')

    for index, item in enumerate(excluded):
        label = 'goals.excluded[' + str(index) + ']'
        if not isinstance(item, dict):
            errors.append(label + ' must be an object')
            continue
        ident = item.get('id')
        if not isinstance(ident, str) or not ident.strip() or ident in all_ids:
            errors.append(label + ' id missing or duplicated')
        else:
            all_ids.add(ident)
        for key in ('item', 'source'):
            value = item.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(label + ' ' + key + ' required')

    for ident, references in evidence_map.items():
        if not isinstance(ident, str) or ident not in included_ids:
            errors.append('goals.evidence_map contains unknown goal id')
            continue
        label = 'goals.evidence_map.' + ident
        if not isinstance(references, list):
            errors.append(label + ' must be a list')
        elif not references:
            errors.append(label + ' requires nonempty evidence references')
        else:
            for index, reference in enumerate(references):
                if isinstance(reference, str) and reference.strip():
                    continue  # Legacy references remain readable but do not prove completion.
                errors.extend(
                    f'{label}[{index}] {error}' for error in evidence_record_errors(reference)
                )

    if require_completion_evidence:
        for ident in sorted(included_ids):
            references = evidence_map.get(ident)
            if not references:
                errors.append('goal evidence missing: ' + ident)
            elif not has_goal_evidence(references):
                errors.append('goal evidence requires a verified observation: ' + ident)
    return errors


def validate_completion_accounting(s, goals):
    """Validate evidence-based completion versus an explicit user-requested close."""
    errors = []
    if not isinstance(goals, dict):
        goals = {}
    basis = s.get('completion_basis', 'evidence')
    if not isinstance(basis, str) or basis not in COMPLETION_BASES:
        errors.append('invalid completion_basis')
    unverified = s.get('unverified_goals', [])
    if not isinstance(unverified, list):
        errors.append('unverified_goals must be a list')
        unverified = []
    included_items = goals.get('included', [])
    if not isinstance(included_items, list):
        included_items = []
    included_ids = {
        item.get('id') for item in included_items
        if isinstance(item, dict) and isinstance(item.get('id'), str)
    }
    seen = set()
    for index, item in enumerate(unverified):
        label = 'unverified_goals[' + str(index) + ']'
        if not isinstance(item, dict):
            errors.append(label + ' must be an object')
            continue
        ident = item.get('id')
        if not isinstance(ident, str) or ident not in included_ids or ident in seen:
            errors.append(label + ' id must reference a unique included goal')
        else:
            seen.add(ident)
        for key in ('item', 'reason', 'impact'):
            value = item.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(label + ' ' + key + ' required')
    if basis == 'user_requested':
        source = s.get('completion_request_source')
        if not isinstance(source, str) or not source.strip():
            errors.append('user requested completion requires source')
        evidence_map = goals.get('evidence_map')
        if not isinstance(evidence_map, dict):
            evidence_map = {}
        missing = [ident for ident in sorted(included_ids) if not has_goal_evidence(evidence_map.get(ident))]
        missing_unverified = set(missing) - seen
        if missing_unverified:
            errors.append(
                'user requested completion must record unverified goals: ' +
                ', '.join(sorted(missing_unverified))
            )
        report = s.get('completion_report')
        if not isinstance(report, dict):
            errors.append('user requested completion requires completion_report')
        else:
            verified_ids = report.get('verified_goal_ids')
            unverified_ids = report.get('unverified_goal_ids')
            expected_unverified = set(seen)
            expected_verified = included_ids - expected_unverified
            if not isinstance(verified_ids, list) or any(
                    not isinstance(item, str) or not item for item in verified_ids):
                errors.append('completion_report.verified_goal_ids must be a nonempty string list')
            elif set(verified_ids) != expected_verified:
                errors.append('completion_report.verified_goal_ids must match evidenced included goals')
            if not isinstance(unverified_ids, list) or any(
                    not isinstance(item, str) or not item for item in unverified_ids):
                errors.append('completion_report.unverified_goal_ids must be a nonempty string list')
            elif set(unverified_ids) != expected_unverified:
                errors.append('completion_report.unverified_goal_ids must match unverified_goals')
    elif unverified:
        errors.append('unverified goals require user_requested completion')
    return errors


def validate_plan_steps(plan, require_steps=False, require_complete=False):
    """Validate the numbered plan and its one-at-a-time progress order."""
    errors = []
    steps = plan.get('steps')
    if steps is None:
        if require_steps:
            errors.append('presented plan requires numbered steps')
        return errors
    if not isinstance(steps, list):
        return ['plan.steps must be a list']
    if require_steps and not steps:
        errors.append('presented plan requires at least one numbered step')

    ids, first_unfinished = set(), None
    in_progress_count = 0
    for index, step in enumerate(steps):
        label = 'plan.steps[' + str(index) + ']'
        if not isinstance(step, dict):
            errors.append(label + ' must be an object')
            continue
        ident = step.get('id')
        if not isinstance(ident, str) or not ident.strip() or ident in ids:
            errors.append(label + ' id missing or duplicated')
        else:
            ids.add(ident)
        action = step.get('action')
        if not isinstance(action, str) or not action.strip():
            errors.append(label + ' action required')
        status = step.get('status')
        if status not in STEP_STATUSES:
            errors.append(label + ' status must be pending, in_progress, done, or blocked')
            continue
        if status == 'in_progress':
            in_progress_count += 1
        if status == 'done':
            evidence = step.get('evidence')
            if isinstance(evidence, list):
                valid_evidence = bool(evidence) and all(isinstance(item, str) and item.strip() for item in evidence)
            else:
                valid_evidence = isinstance(evidence, str) and bool(evidence.strip())
            if not valid_evidence:
                errors.append(label + ' done requires evidence')
            if first_unfinished is not None:
                errors.append(label + ' cannot be done after an unfinished step')
        else:
            if first_unfinished is None:
                first_unfinished = ident or label
            elif status in ('in_progress', 'blocked'):
                errors.append(label + ' cannot start or block after an earlier unfinished step')
            if status == 'blocked':
                reason = step.get('reason')
                if not isinstance(reason, str) or not reason.strip():
                    errors.append(label + ' blocked requires reason')

    if in_progress_count > 1:
        errors.append('plan cannot have more than one in_progress step')
    if require_complete and first_unfinished is not None:
        errors.append('unfinished plan steps prevent completion: ' + str(first_unfinished))
    return errors


def validate_user_requested_steps(s, plan):
    """User-requested close must enumerate every unfinished step."""
    if s.get('completion_basis') != 'user_requested':
        return []
    steps = plan.get('steps') if isinstance(plan, dict) else []
    if not isinstance(steps, list):
        return []
    unfinished = [
        step for step in steps
        if isinstance(step, dict) and step.get('status') != 'done'
    ]
    if not unfinished:
        return []
    records = s.get('unverified_plan_steps')
    if not isinstance(records, list):
        return ['user requested completion requires unverified_plan_steps']
    errors, seen = [], set()
    unfinished_ids = {
        step.get('id') for step in unfinished if isinstance(step.get('id'), str)
    }
    unfinished_actions = {
        step.get('id'): step.get('action') for step in unfinished
        if isinstance(step.get('id'), str)
    }
    for index, item in enumerate(records):
        label = 'unverified_plan_steps[' + str(index) + ']'
        if not isinstance(item, dict):
            errors.append(label + ' must be an object')
            continue
        ident = item.get('id')
        if not isinstance(ident, str) or ident not in unfinished_ids or ident in seen:
            errors.append(label + ' id must reference a unique unfinished step')
        else:
            seen.add(ident)
        for key in ('reason', 'impact'):
            value = item.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(label + ' ' + key + ' required')
        action = item.get('action')
        if not isinstance(action, str) or not action.strip():
            errors.append(label + ' action required')
        elif ident in unfinished_actions and action != unfinished_actions[ident]:
            errors.append(label + ' action must match the unfinished plan step')
    missing = unfinished_ids - seen
    if missing:
        errors.append('user requested completion must record unfinished steps: ' + ', '.join(sorted(missing)))
    return errors


def host_objectives_match(s, host_id, allow_superseded=False):
    """Compare readback, not requested text. A superseded mapping is for acceptance only."""
    goals = s.get('goals')
    items = goals.get('included') if isinstance(goals, dict) else None
    mode = s.get('goal_tracking_host_kind')
    rows = s.get('goal_tracking_host_readback')
    if mode not in ('aggregate', 'task_list') or not isinstance(items, list):
        return False
    blocks = {}
    for item in items:
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item[k].strip()
                                                for k in ('id', 'criterion')):
            return False
        blocks[item['id']] = item['id'] + '：' + item['criterion'].replace('\r\n', '\n').strip()
    stale = {}
    old = s.get('superseded_goals')
    if allow_superseded and s.get('host_goal_sync') in ('stale', 'unavailable') and isinstance(old, list):
        stale = {g['host_id']: g for g in old if isinstance(g, dict) and isinstance(g.get('host_id'), str)}
    if not isinstance(host_id, str):
        return False
    if mode == 'aggregate' and host_id in stale:
        return True  # Entire aggregate was superseded; never used to authorize new work.
    if not isinstance(rows, list) or not rows:
        return False
    texts = {}
    for row in rows:
        if not isinstance(row, dict):
            return False
        ident, objective = row.get('host_id'), row.get('objective')
        if not isinstance(ident, str) or not ident.strip() or ident in texts or not isinstance(objective, str):
            return False
        texts[ident] = objective.replace('\r\n', '\n').strip()
    if host_id not in texts or not blocks:
        return False
    if mode == 'aggregate':
        return len(texts) == 1 and texts[host_id] == '\n'.join(blocks.values())
    expected = {v: k for k, v in blocks.items()}
    unresolved = set(blocks)
    pending = []
    for ident, text in texts.items():
        key = expected.get(text)
        if key in unresolved:
            unresolved.remove(key)
        else:
            pending.append((ident, text))
    for ident, text in pending:
        old_goal = stale.get(ident)
        if not old_goal or not isinstance(old_goal.get('objective'), str) or text != old_goal['objective'].strip():
            return False
        targets = old_goal.get('replacement_goal_ids')
        if not isinstance(targets, list):
            return False
        for key in targets:
            if not isinstance(key, str) or key not in unresolved:
                return False
            unresolved.remove(key)
    return not unresolved


def validate_goal_tracking(s, allow_superseded=False):
    errors = []
    mode = s.get('goal_tracking_mode')
    source = s.get('goal_tracking_source')
    confirmation = s.get('goal_tracking_confirmation_source')
    if not isinstance(mode, str) or mode not in GOAL_TRACKING_MODES:
        errors.append('goal_tracking_mode must be host, plan, conversation, or unavailable')
    if not isinstance(source, str) or not source.strip():
        errors.append('goal_tracking_source required')
    if not isinstance(confirmation, str) or not confirmation.strip():
        errors.append('goal_tracking_confirmation_source required')
    if mode == 'host':
        host_id = s.get('goal_tracking_host_id')
        if not isinstance(host_id, str) or not host_id.strip():
            errors.append('host goal tracking requires goal_tracking_host_id')
        host_receipt = s.get('goal_tracking_host_receipt')
        if not isinstance(host_receipt, str) or not host_receipt.strip():
            errors.append('host goal tracking requires goal_tracking_host_receipt')
        if not host_objectives_match(s, host_id, allow_superseded):
            errors.append('host goal readback must match confirmed goal IDs and criteria; read the actual host objective')

    elif mode in GOAL_TRACKING_FALLBACK_MODES:
        reason = s.get('goal_tracking_fallback_reason')
        evidence = s.get('goal_tracking_fallback_evidence')
        if not isinstance(reason, str) or not reason.strip():
            errors.append('fallback goal tracking requires goal_tracking_fallback_reason')
        if not isinstance(evidence, str) or not evidence.strip():
            errors.append('fallback goal tracking requires goal_tracking_fallback_evidence')
        goals = s.get('goals')
        local_goal_id = goals.get('local_goal_id') if isinstance(goals, dict) else None
        if not isinstance(local_goal_id, str) or not local_goal_id.strip():
            errors.append('fallback goal tracking requires goals.local_goal_id')
    elif mode == 'unavailable':
        errors.append('unavailable goal tracking cannot enter execution')
    return errors


def accepting_superseded(s):
    """Never offer an execution, repair, local action or new grant under an old scope."""
    return (s.get('goal_tracking_mode') == 'host' and s.get('host_goal_sync') in ('stale', 'unavailable')
            and s.get('execution_begun') is True and not s.get('interruptions')
            and not s.get('independent_action')
            and (not s.get('local_only') or (s.get('local_only_read_only') is True
                 and isinstance(s.get('local_only_source'), str) and s['local_only_source'].strip()))
            and (s.get('status') == 'complete' or
                 (s.get('phase') in ('verification', 'review') and s.get('read_only') is True)))


def validate_execution_entry(s):
    """Require explicit closure and a bounded mutation scope before execution."""
    errors = []
    if s.get('analysis_complete') is not True:
        errors.append('analysis_complete must be true before execution')
    if not isinstance(s.get('analysis_evidence'), str) or not s['analysis_evidence'].strip():
        errors.append('analysis_evidence required before execution')
    if s.get('discussion_closed') is not True:
        errors.append('discussion_closed must be true before execution')
    if (not isinstance(s.get('discussion_closure_source'), str) or
            not s['discussion_closure_source'].strip()):
        errors.append('discussion_closure_source required before execution')

    scope = s.get('execution_scope')
    if not isinstance(scope, dict):
        errors.append('execution_scope required before execution')
    else:
        allowed_paths = scope.get('allowed_paths')
        allowed_actions = scope.get('allowed_actions')
        if (not isinstance(allowed_paths, list) or not allowed_paths or
                any(not isinstance(path, str) or not path.strip() for path in allowed_paths)):
            errors.append('execution_scope.allowed_paths requires nonempty paths')
        if (not isinstance(allowed_actions, list) or not allowed_actions or
                any(not isinstance(action, str) or not action.strip() for action in allowed_actions)):
            errors.append('execution_scope.allowed_actions requires nonempty actions')
        else:
            steps = s.get('plan', {}).get('steps', []) if isinstance(s.get('plan'), dict) else []
            if isinstance(steps, list):
                for index, step in enumerate(steps):
                    if (isinstance(step, dict) and isinstance(step.get('action'), str) and
                            step['action'] not in allowed_actions):
                        errors.append(
                            'plan.steps[' + str(index) + '] action is not in execution_scope.allowed_actions'
                        )
        if (not isinstance(scope.get('source'), str) or
                not scope['source'].strip()):
            errors.append('execution_scope.source required')
        if 'subagent_policy' in scope:
            policy = scope['subagent_policy']
            if (not isinstance(policy, dict) or
                    policy.get('execution') not in ('as_needed', 'disabled') or
                    policy.get('review') not in ('enabled', 'disabled')):
                errors.append('execution_scope.subagent_policy requires execution and review modes')
            elif ('restriction' in policy and
                  (not isinstance(policy['restriction'], str) or not policy['restriction'].strip())):
                errors.append('execution_scope.subagent_policy.restriction must be nonempty text')

    if s.get('execution_begun') is True:
        receipt = s.get('execution_receipt')
        if not isinstance(receipt, str) or not receipt.strip():
            errors.append('execution_begun requires execution_receipt')
        elif not re.fullmatch(r'[0-9a-f]{64}', receipt):
            errors.append('execution_receipt must be a sha256 value')
        elif receipt != execution_receipt(s):
            prior = s.get('prior_execution_authorization')
            if not (accepting_superseded(s) and isinstance(prior, dict)
                    and prior.get('task_id') == s.get('task_id')
                    and receipt == authorization_hash(prior)):
                errors.append('execution_receipt does not match current authorization')
    elif 'execution_begun' in s and not isinstance(s.get('execution_begun'), bool):
        errors.append('execution_begun must be boolean')
    return errors


def execution_authorization_payload(s):
    """Return the stable part of an execution grant used for its receipt."""
    plan = s.get('plan') if isinstance(s.get('plan'), dict) else {}
    goals = s.get('goals') if isinstance(s.get('goals'), dict) else {}
    scope = s.get('execution_scope') if isinstance(s.get('execution_scope'), dict) else {}
    steps = plan.get('steps') if isinstance(plan.get('steps'), list) else []
    return {
        'task_id': s.get('task_id'),
        'analysis_evidence': s.get('analysis_evidence'),
        'discussion_closure_source': s.get('discussion_closure_source'),
        'plan': {
            'evidence': plan.get('evidence'),
            'presentation_id': plan.get('presentation_id'),
            'steps': [
                {'id': step.get('id'), 'action': step.get('action')}
                for step in steps if isinstance(step, dict)
            ],
        },
        'goals': {
            'evidence': goals.get('evidence'),
            'presentation_id': goals.get('presentation_id'),
            'local_goal_id': goals.get('local_goal_id'),
            'included': goals.get('included'),
            'excluded': goals.get('excluded'),
        },
        'gates': s.get('gates'),
        'goal_tracking': {
            'mode': s.get('goal_tracking_mode'),
            'source': s.get('goal_tracking_source'),
            'confirmation_source': s.get('goal_tracking_confirmation_source'),
            'host_id': s.get('goal_tracking_host_id'),
            'host_receipt': s.get('goal_tracking_host_receipt'),
            'fallback_reason': s.get('goal_tracking_fallback_reason'),
            'fallback_evidence': s.get('goal_tracking_fallback_evidence'),
        },
        'execution_scope': scope,
    }


def execution_receipt(s):
    return authorization_hash(execution_authorization_payload(s))


def authorization_hash(payload):
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def independent_action_allowed(s):
    """Permit wait-period work only when it is read-only or fully gated execution."""
    if s.get('independent_action_read_only') is True:
        scope = s.get('read_only_scope')
        action = s.get('independent_action')
        if not isinstance(scope, dict) or not isinstance(action, str):
            return False
        allowed_actions = scope.get('allowed_actions')
        source = scope.get('source')
        return (
            isinstance(allowed_actions, list) and
            isinstance(source, str) and bool(source.strip()) and
            any(isinstance(item, str) and item.strip() == action.strip() for item in allowed_actions)
        )
    if not (
        s.get('analysis_complete') is True and
        isinstance(s.get('analysis_evidence'), str) and s['analysis_evidence'].strip() and
        s.get('discussion_closed') is True and
        isinstance(s.get('discussion_closure_source'), str) and s['discussion_closure_source'].strip() and
        isinstance(s.get('plan'), dict) and s['plan'].get('presented') is True and
        isinstance(s.get('goals'), dict) and s['goals'].get('presented') is True and
        isinstance(s.get('execution_scope'), dict) and
        s.get('execution_begun') is True and
        isinstance(s.get('execution_receipt'), str) and
        s['execution_receipt'] == execution_receipt(s)
    ):
        return False
    gates = s.get('gates')
    if not isinstance(gates, dict) or any(not gates.get(name) for name in GATES):
        return False
    if validate_execution_entry(s) or validate_goal_tracking(s):
        return False
    action = s.get('independent_action')
    allowed_actions = s.get('execution_scope', {}).get('allowed_actions')
    if not isinstance(allowed_actions, list) or not isinstance(action, str):
        return False
    return any(isinstance(item, str) and item.strip() == action.strip() for item in allowed_actions)


def goal_scope_requires_previous(s):
    if not isinstance(s, dict):
        return False
    goals = s.get('goals')
    if not isinstance(goals, dict) or goals.get('presented') is not True:
        return False
    if not isinstance(goals.get('included'), list) and not isinstance(goals.get('excluded'), list):
        return False
    return s.get('status') == 'complete' or s.get('phase') in ('execution', 'verification', 'review')



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
    errors.extend(validate_plan_steps(plan, require_steps=plan.get('presented') is True))
    goals = s.get('goals')
    completion_basis = s.get('completion_basis', 'evidence')
    if goals is not None:
        if not isinstance(goals, dict) or not isinstance(goals.get('presented'), bool):
            errors.append('goals.presented must be true or false')
        elif goals['presented'] and (not isinstance(goals.get('evidence'), str) or not goals['evidence'].strip()):
            errors.append('presented goals require evidence')
        if (isinstance(goals, dict) and goals.get('presented') is True and
                plan.get('presented') is not True and s.get('plan_required', True) is not False):
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
            if isinstance(goals.get('local_goal_id'), str) and not goals['local_goal_id'].strip():
                errors.append('goals.local_goal_id cannot be empty')
            elif 'local_goal_id' in goals and not isinstance(goals.get('local_goal_id'), str):
                errors.append('goals.local_goal_id must be a string')
            if (goals.get('presented') is True or
                    any(key in goals for key in (
                        'included', 'excluded', 'evidence_map', 'evidence', 'presentation_id'))):
                errors.extend(validate_goal_scope(
                    goals,
                    require_completion_evidence=(
                        s.get('status') == 'complete' and
                        completion_basis != 'user_requested'
                    ),
                    allow_empty_included=(
                        s.get('status') == 'complete' and
                        completion_basis == 'user_requested'
                    ),
                ))
                scope_was_presented = (
                    goals.get('presented') is True or
                    any(key in goals for key in (
                        'included', 'excluded', 'evidence_map', 'evidence', 'presentation_id'))
                )
                if scope_was_presented:
                    baseline = s.get('goal_scope_baseline')
                    if not isinstance(baseline, dict):
                        errors.append('goal_scope_baseline required for a presented or hidden goal')
                    elif (baseline.get('included'), baseline.get('excluded')) != (
                            goals.get('included'), goals.get('excluded')):
                        errors.append('goal_scope_baseline must match current included/excluded')
            errors.extend(validate_completion_accounting(s, goals))
    superseded_goals = s.get('superseded_goals', [])
    if not isinstance(superseded_goals, list):
        errors.append('superseded_goals must be a list')
    else:
        for item in superseded_goals:
            if not isinstance(item, dict):
                errors.append('superseded goal must be an object')
                continue
            for key in ('objective', 'source', 'superseded_by'):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    errors.append('superseded goal ' + key + ' required')
            host_id = item.get('host_id')
            local_goal_id = item.get('local_goal_id')
            if host_id is not None and not isinstance(host_id, str):
                errors.append('superseded goal host_id must be a string or null')
            if local_goal_id is not None and not isinstance(local_goal_id, str):
                errors.append('superseded goal local_goal_id must be a string or null')
            if not ((isinstance(host_id, str) and host_id.strip()) or
                    (isinstance(local_goal_id, str) and local_goal_id.strip())):
                errors.append('superseded goal requires host_id or local_goal_id')
    host_goal_sync = s.get('host_goal_sync')
    if host_goal_sync not in (None, 'synced', 'stale', 'unavailable'):
        errors.append('invalid host goal sync status')
    elif host_goal_sync in ('stale', 'unavailable') and not superseded_goals:
        errors.append('stale or unavailable host goal requires superseded_goals')
    if host_goal_sync in ('synced', 'stale'):
        has_host_id = any(
            isinstance(item, dict) and isinstance(item.get('host_id'), str) and item['host_id'].strip()
            for item in superseded_goals
        )
        if not has_host_id:
            errors.append('host goal sync requires a nonempty host_id')
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
    if (plan_required is False and
            (s.get('phase') == 'execution' or
             (s.get('phase') in ('verification', 'review') and
              s.get('execution_occurred') is not False))):
        errors.append('plan cannot be waived for execution or later')
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
    if s.get('local_only') is True and s.get('phase') == 'execution':
        if (not isinstance(s.get('local_only_source'), str) or
                not s['local_only_source'].strip()):
            errors.append('local_only execution requires local_only_source')
    if s.get('local_only') is True and s.get('phase') in ('analysis', 'discussion', 'planning', 'goals'):
        if (not isinstance(s.get('local_only_source'), str) or
                not s['local_only_source'].strip()):
            errors.append('local_only before execution requires local_only_source')
        if s.get('local_only_read_only') is not True:
            errors.append('local_only before execution must be read-only')
    if s.get('local_only') is True and s.get('local_done') is True:
        steps = s.get('plan', {}).get('steps', []) if isinstance(s.get('plan'), dict) else []
        if (isinstance(steps, list) and
                any(isinstance(step, dict) and step.get('status') != 'done' for step in steps)):
            errors.append('local_done cannot bypass unfinished plan steps')
    if 'independent_action_read_only' in s and not isinstance(s.get('independent_action_read_only'), bool):
        errors.append('independent_action_read_only must be boolean')
    if (s.get('independent_action_read_only') is True and
            isinstance(s.get('independent_action'), str) and s['independent_action'].strip()):
        read_only_scope = s.get('read_only_scope')
        if not isinstance(read_only_scope, dict):
            errors.append('read-only independent action requires read_only_scope')
        else:
            allowed_actions = read_only_scope.get('allowed_actions')
            action = s.get('independent_action')
            if (not isinstance(allowed_actions, list) or not allowed_actions or
                    any(not isinstance(item, str) or not item.strip() for item in allowed_actions)):
                errors.append('read_only_scope.allowed_actions requires nonempty actions')
            elif not isinstance(action, str) or action.strip() not in allowed_actions:
                errors.append('independent_action must be listed in read_only_scope.allowed_actions')
            if not isinstance(read_only_scope.get('source'), str) or not read_only_scope['source'].strip():
                errors.append('read_only_scope.source required')
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
    if phase in ('verification', 'review') and s.get('execution_occurred') is False and s.get('read_only') is not True:
        errors.append('verification/review without execution requires read_only:true')
    if 'read_only' in s and not isinstance(s.get('read_only'), bool):
        errors.append('read_only must be boolean')
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
        evidence = op.get('evidence')
        if op.get('status') in ('failed', 'succeeded') and (not isinstance(evidence, str) or not evidence.strip()):
            errors.append('operation result requires evidence')
        for key in ('evidence_revision', 'next_dependency_evidence'):
            if key in op and (not isinstance(op[key], str) or not op[key].strip()):
                errors.append('operation ' + key + ' must be nonempty text')
        if 'evidence_revision' in op and (not isinstance(evidence, str) or not evidence.strip()):
            errors.append('operation evidence_revision requires evidence')
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
        if s.get('status') in ('continue', 'complete') and not querying_operation:
            errors.extend(validate_goal_tracking(s, allow_superseded=accepting_superseded(s)))
            errors.extend(validate_execution_entry(s))
            errors.extend(validate_plan_steps(
                plan,
                require_steps=True,
                require_complete=(
                    s.get('status') == 'complete' and
                    completion_basis != 'user_requested'
                ),
            ))
            if phase in ('verification', 'review') and s.get('execution_begun') is not True:
                errors.append('verification or review of executed work requires execution begin')
        for name in GATES:
            if not gates.get(name) and not (name in ('execution', 'subagents') and querying_operation):
                errors.append(name + ' evidence required for execution or later')
        if s.get('status') == 'complete':
            if s.get('execution_begun') is not True:
                errors.append('execution_begun must be true before completion')
            if not isinstance(s.get('execution_receipt'), str) or not s['execution_receipt'].strip():
                errors.append('completion requires execution_receipt')
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
        if not isinstance(goals, dict) or goals.get('presented') is not True:
            errors.append('required goals must be presented before completion')
        if isinstance(goals, dict) and goals.get('status') == 'superseded':
            errors.append('superseded goals cannot be used for completion')
        if plan_required is not False and s.get('phase') in ('discussion', 'planning') and s.get('coverage_checked') is not True:
            errors.append('coverage check required before completion')
        if any(i.get('status') == 'pending' and i.get('blocks_completion', True) is not False for i in items if isinstance(i, dict)):
            errors.append('pending decisions prevent completion')
        if not isinstance(s.get('completion_evidence'), str) or not s['completion_evidence'].strip():
            errors.append('completion evidence required')
        if (s.get('phase') in ('execution', 'verification', 'review') and
                s.get('execution_occurred') is not False and
                completion_basis != 'user_requested'):
            errors.extend(validate_plan_steps(plan, require_steps=True, require_complete=True))
        if completion_basis == 'user_requested':
            errors.extend(validate_user_requested_steps(s, plan))
    return errors


def operations_by_id(state):
    operations = state.get('operations', [])
    if not isinstance(operations, list):
        return {}
    return {op['id']: op for op in operations
            if isinstance(op, dict) and isinstance(op.get('id'), str)}


def has_new_source(value, previous, *, normalize_spacing=False):
    if not isinstance(value, str):
        return False
    previous = previous if isinstance(previous, str) else ''
    if normalize_spacing:
        value = ''.join(value.split())
        previous = ''.join(previous.split())
    return bool(value.strip()) and value.strip() != previous.strip()


def validate_operation_transition(previous, current, confirmed_scope_change):
    errors = []
    current_operations = operations_by_id(current)
    for ident, old in operations_by_id(previous).items():
        pending = old.get('status') in ('running', 'unknown')
        blocking = old.get('blocks_next') or old.get('blocks_completion', True)
        if not (pending and old.get('side_effect') or
                (pending or old.get('status') == 'failed') and blocking):
            continue
        observed = current_operations.get(ident)
        if observed is None or observed.get('reference') != old.get('reference'):
            problem = 'unresolved' if pending else 'blocking failed'
            errors.append(problem + ' operation must keep its id and reference: ' + ident)
            continue
        if old.get('side_effect') is True and observed.get('side_effect') is False:
            errors.append('unresolved operation cannot discard its side effect: ' + ident)
        new_status = observed.get('status')
        fresh_evidence = (has_new_source(observed.get('evidence'), old.get('evidence')) or
                          has_new_source(observed.get('evidence_revision'), old.get('evidence_revision'),
                                         normalize_spacing=True))
        if new_status in ('succeeded', 'failed') and new_status != old.get('status') and not fresh_evidence:
            errors.append('operation result requires new evidence: ' + ident)
        if new_status == 'succeeded':
            continue
        handled_failure = old.get('status') == new_status == 'failed' and fresh_evidence
        read_only_pending = (new_status in ('running', 'unknown') and
                             old.get('side_effect') is False and observed.get('side_effect') is False)
        next_is_independent = (pending and read_only_pending and
                               has_new_source(observed.get('next_dependency_evidence'),
                                              old.get('next_dependency_evidence'), normalize_spacing=True))
        if (old.get('blocks_next') is True and observed.get('blocks_next') is False and
                not (handled_failure or next_is_independent)):
            errors.append('unresolved operation cannot stop blocking next: ' + ident)
        if old.get('blocks_completion', True) and observed.get('blocks_completion') is False:
            observed_scope = read_only_pending and fresh_evidence
            if not (confirmed_scope_change or observed_scope or handled_failure):
                errors.append('unresolved operation cannot stop blocking completion without scope evidence: ' + ident)
    return errors


def validate_transition(previous, current):
    """Check explicit changes when both snapshots are available; never infer intent."""
    if not isinstance(previous, dict) or not isinstance(current, dict):
        return ['previous and current states must be objects']
    errors = []
    if previous.get('task_id') != current.get('task_id'):
        errors.append('task id changed')
    previous_goals = previous.get('goals')
    if isinstance(previous_goals, dict) and (
            previous_goals.get('presented') is True or
            any(key in previous_goals for key in (
                'included', 'excluded', 'evidence_map', 'evidence', 'presentation_id'))):
        previous_baseline = previous.get('goal_scope_baseline')
        if not isinstance(previous_baseline, dict):
            errors.append('goal_scope_baseline required for previous goal state')
        elif (previous_baseline.get('included'), previous_baseline.get('excluded')) != (
                previous_goals.get('included'), previous_goals.get('excluded')):
            errors.append('previous goal_scope_baseline must match previous included/excluded')
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
        history = list(previous.get('branch_history', []))
        if len(new_ids) + 1 == len(old_ids):
            closed = old_frames[-1]
            if 'branch' in closed:
                history.append(branch_record(closed))
            if unrelated_closed(closed):
                parent = new_frames[-1] if new_frames else current
                if not has_return_consent(closed) or make_resume_point(parent) != closed['resume_point']:
                    errors.append('return requires explicit agreement and the original pending point')
        if current.get('branch_history', []) != history:
            errors.append('preserve branch history and archive the reconciled branch')
        if any('return_answer' in frame for frame in new_frames[common:]):
            errors.append('return answer requires a preceding interruption with a presented question')
        for old, new in zip(old_frames[:common], new_frames[:common]):
            if old['id'] != new['id']:
                continue
            branch_changed = False
            if 'branch' in old:
                branch = new.get('branch', {})
                if not branch or old['branch']['origin'] != branch.get('origin'):
                    errors.append('recorded branch must retain its origin')
                branch_changed = any(old['branch'].get(key) != branch.get(key)
                                     for key in ('relation', 'target', 'impact'))
                if branch_changed and not has_new_source(
                        new.get('branch_revision_source'), old.get('branch_revision_source')):
                    errors.append('branch changes require fresh revision evidence')
                if old.get('branch_revision_source') and not new.get('branch_revision_source'):
                    errors.append('preserve the recorded branch revision source')
            instruction_changed = (new.get('return_instruction_source') is not None and
                                   new.get('return_instruction_source') != old.get('return_instruction_source'))
            if instruction_changed and not all(has_new_source(new.get('return_instruction_source'), source)
                                               for source in (old.get('return_instruction_source'),
                                                              old.get('return_answer_source'))):
                errors.append('return instruction requires a fresh user source')
            clearing_return = (new.get('return_answer') is None and
                               (instruction_changed or branch_changed and
                                new.get('branch', {}).get('relation') == 'related'))
            if new.get('return_answer') != old.get('return_answer') and not clearing_return:
                if (not old.get('return_question_source') or
                        old['return_question_source'] != new.get('return_question_source') or
                        not has_new_source(new.get('return_answer_source'), old.get('return_answer_source'))):
                    errors.append('return answer requires the preceding question and a fresh reply')
            if old['request'] != new['request'] and old['source'] == new['source']:
                errors.append('changed interruption request requires new source')
            if old.get('resume_point') is not None and old.get('resume_point') != new.get('resume_point'):
                errors.append('saved interruption resume_point cannot change')
            if old['status'] == 'paused' and new['status'] not in ('paused', 'cancelled'):
                if not has_new_source(new.get('resume_source'), old.get('resume_source')):
                    errors.append('resuming paused interruption requires source')
            if old['status'] in ('complete', 'cancelled') and new['status'] != old['status']:
                errors.append('completed interruption cannot change status')
    old_plan, new_plan = previous.get('plan'), current.get('plan')
    old_plan_unshown = isinstance(old_plan, dict) and old_plan.get('presented') is False
    old_plan_shown = isinstance(old_plan, dict) and old_plan.get('presented') is True
    new_plan_unshown = isinstance(new_plan, dict) and new_plan.get('presented') is False
    new_plan_shown = isinstance(new_plan, dict) and new_plan.get('presented') is True
    first_display = not old_plan_shown and new_plan_shown
    if first_display and not old_plan_unshown:
        errors.append('formal plan display requires the preceding discussion or presentation state')
    revision_source = current.get('plan_revision_source')
    if (old_plan_shown and new_plan_unshown and
            (not isinstance(revision_source, str) or not revision_source.strip() or
             revision_source == previous.get('plan_revision_source'))):
        errors.append('a previously presented formal plan must retain its presentation state without a revision source')
    old_goals_shown = isinstance(previous_goals, dict) and previous_goals.get('presented') is True
    entered_planning = (previous.get('phase') == 'discussion' and current.get('phase') == 'planning' and
                        (not old_plan_shown or old_goals_shown))
    confirmed = discussion_transition_confirmed(current)
    if (first_display or entered_planning) and (not confirmed or not discussion_ready(current)):
        errors.append('first formal plan presentation requires confirmed discussion transition')
    if first_display:
        new_goals = current.get('goals')
        if not isinstance(new_goals, dict) or new_goals.get('presented') is not True:
            errors.append('first formal plan and goals must be presented together')
    current_goals = current.get('goals')
    reopening_discussion = (current.get('phase') == 'discussion' and
                            new_plan_shown and
                            isinstance(current_goals, dict) and current_goals.get('presented') is True)
    if (new_plan_unshown or first_display or entered_planning or reopening_discussion) and confirmed:
        follows_confirmed_discussion = (old_plan_unshown or
                                        (old_plan_shown and new_plan_shown and
                                         previous.get('phase') == 'discussion' and
                                         previous.get('status') == 'continue'))
        same_closure = (follows_confirmed_discussion and discussion_transition_confirmed(previous) and
                        all(previous.get(key) == current.get(key) for key in
                            ('discussion_closure_question_source', 'discussion_closure_source')))
        waiting_for_question = (previous.get('phase') == 'discussion' and
                                discussion_transition_waiting(previous) and
                                previous.get('wait_evidence') == current.get('discussion_closure_question_source'))
        if not (same_closure or waiting_for_question):
            errors.append('discussion transition answer must match the preceding question')
        if (not discussion_ready(previous) or not discussion_ready(current) or
                discussion_decisions(previous) != discussion_decisions(current) or
                previous.get('confirmed_requirements', []) != current.get('confirmed_requirements', [])):
            errors.append('discussion transition must be reconfirmed after a material change')
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
        if not has_new_source(current.get('resume_source'), previous.get('resume_source')):
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
    pending_scoped_plan = (old_plan_unshown and previous.get('plan_requested') is True and
                           previous.get('phase') in ('discussion', 'planning') and
                           previous.get('status') in ('continue', 'wait_user', 'wait_tool') and
                           current.get('phase') in ('discussion', 'planning') and
                           current.get('status') in ('continue', 'wait_user', 'wait_tool'))
    if (previous.get('scope_limited') is True and current.get('scope_limited') is True and
            scope_state_changed and
            not pending_scoped_plan and
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
        if (not isinstance(current.get('plan_revision_source'), str) or
                not current['plan_revision_source'].strip()):
            errors.append('changed plan evidence requires plan_revision_source')
        elif current.get('plan_revision_source') == previous.get('plan_revision_source'):
            errors.append('changed plan evidence requires a new plan_revision_source')
    old_execution_begun = previous.get('execution_begun') is True
    new_execution_begun = current.get('execution_begun') is True
    previous_authorization = execution_authorization_payload(previous)
    current_authorization = execution_authorization_payload(current)
    if (new_execution_begun and not old_execution_begun and
            (previous.get('phase') != 'execution' or previous.get('status') != 'continue' or
             previous_authorization != current_authorization)):
        errors.append('starting execution requires the matching state used for begin')
    if old_execution_begun and not new_execution_begun:
        if (not isinstance(current.get('execution_reset_source'), str) or
                not current['execution_reset_source'].strip()):
            errors.append('stopping begun execution requires execution_reset_source')
    if (old_execution_begun and new_execution_begun and
            current.get('execution_receipt') != previous.get('execution_receipt') and
            current.get('execution_receipt') == authorization_hash(current_authorization) and
            previous_authorization != current_authorization):
        errors.append('changed execution authorization requires stopping and a new begin')
    old_scope = previous.get('execution_scope')
    new_scope = current.get('execution_scope')
    if old_scope != new_scope:
        if old_execution_begun and not new_execution_begun and not current.get('execution_reset_source'):
            errors.append('changed execution_scope requires execution_reset_source')
        if old_execution_begun and new_execution_begun:
            errors.append('changed execution_scope requires stopping and a new begin')
        if isinstance(old_scope, dict) and isinstance(new_scope, dict):
            old_boundary = {key: value for key, value in old_scope.items() if key != 'subagent_policy'}
            new_boundary = {key: value for key, value in new_scope.items() if key != 'subagent_policy'}
            old_policy, new_policy = old_scope.get('subagent_policy'), new_scope.get('subagent_policy')
            if old_boundary != new_boundary and old_scope.get('source') == new_scope.get('source'):
                errors.append('changed execution_scope requires a new source')
            if isinstance(old_policy, dict) and isinstance(new_policy, dict):
                if any(old_policy.get(key) != new_policy.get(key) for key in ('execution', 'restriction')):
                    if not has_new_source(new_scope.get('source'), old_scope.get('source')):
                        errors.append('changed execution delegation requires a new execution scope source')
                if old_policy.get('review') != new_policy.get('review'):
                    old_gates, new_gates = previous.get('gates'), current.get('gates')
                    old_review_source = old_gates.get('subagents') if isinstance(old_gates, dict) else None
                    new_review_source = new_gates.get('subagents') if isinstance(new_gates, dict) else None
                    if not has_new_source(new_review_source, old_review_source):
                        errors.append('changed independent review requires a new review source')
        if old_execution_begun and current.get('execution_receipt') == previous.get('execution_receipt'):
            errors.append('changed execution_scope requires a new execution_receipt')
    old_tracking = (
        previous.get('goals', {}).get('local_goal_id') if isinstance(previous.get('goals'), dict) else None,
        previous.get('goal_tracking_mode'),
        previous.get('goal_tracking_source'),
        previous.get('goal_tracking_confirmation_source'),
        previous.get('goal_tracking_host_id'),
        previous.get('goal_tracking_host_receipt'),
        previous.get('goal_tracking_fallback_reason'),
        previous.get('goal_tracking_fallback_evidence'),
    )
    new_tracking = (
        current.get('goals', {}).get('local_goal_id') if isinstance(current.get('goals'), dict) else None,
        current.get('goal_tracking_mode'),
        current.get('goal_tracking_source'),
        current.get('goal_tracking_confirmation_source'),
        current.get('goal_tracking_host_id'),
        current.get('goal_tracking_host_receipt'),
        current.get('goal_tracking_fallback_reason'),
        current.get('goal_tracking_fallback_evidence'),
    )
    if old_tracking != new_tracking:
        if old_execution_begun and not new_execution_begun and not current.get('execution_reset_source'):
            errors.append('changed goal tracking requires execution_reset_source')
        if old_execution_begun and new_execution_begun:
            errors.append('changed goal tracking requires stopping and a new begin')
        if (previous.get('goal_tracking_confirmation_source') ==
                current.get('goal_tracking_confirmation_source')):
            errors.append('changed goal tracking requires a new confirmation source')
        if old_execution_begun and current.get('execution_receipt') == previous.get('execution_receipt'):
            errors.append('changed goal tracking requires a new execution_receipt')
    old_steps = old_plan.get('steps') if isinstance(old_plan, dict) and isinstance(old_plan.get('steps'), list) else []
    new_steps = new_plan.get('steps') if isinstance(new_plan, dict) and isinstance(new_plan.get('steps'), list) else []
    old_steps_by_id = {
        step.get('id'): step for step in old_steps
        if isinstance(step, dict) and isinstance(step.get('id'), str)
    }
    new_steps_by_id = {
        step.get('id'): step for step in new_steps
        if isinstance(step, dict) and isinstance(step.get('id'), str)
    }
    old_step_order = [step.get('id') for step in old_steps if isinstance(step, dict)]
    new_step_order = [step.get('id') for step in new_steps if isinstance(step, dict)]
    for ident in set(old_steps_by_id) & set(new_steps_by_id):
        old_step, new_step = old_steps_by_id[ident], new_steps_by_id[ident]
        if (old_step.get('status') == 'done' and
                old_step.get('action') == new_step.get('action') and
                new_step.get('status') != 'done'):
            errors.append('completed plan step cannot change status')
    same_plan_identity = (
        isinstance(old_plan, dict) and isinstance(new_plan, dict) and
        old_plan.get('evidence') == new_plan.get('evidence') and
        previous.get('phase') == current.get('phase') and
        current.get('phase') in ('execution', 'verification', 'review')
    )
    if same_plan_identity and (old_steps_by_id or new_steps_by_id):
        if set(old_steps_by_id) != set(new_steps_by_id):
            errors.append('plan step ids cannot change without a new plan')
        if old_step_order != new_step_order:
            errors.append('plan step order cannot change')
        for ident in set(old_steps_by_id) & set(new_steps_by_id):
            old_step, new_step = old_steps_by_id[ident], new_steps_by_id[ident]
            if old_step.get('action') != new_step.get('action'):
                errors.append('plan step action cannot change without a new plan')
            old_status, new_status = old_step.get('status'), new_step.get('status')
            if old_status == new_status:
                continue
            if new_status == 'done' and old_status != 'in_progress':
                errors.append('plan step can become done only from in_progress')
            elif new_status == 'in_progress' and old_status not in ('pending', 'blocked'):
                errors.append('plan step can start only from pending or blocked')
        if (set(old_steps_by_id) != set(new_steps_by_id) or
                any(old_steps_by_id.get(ident, {}).get('action') != new_steps_by_id.get(ident, {}).get('action')
                    for ident in set(old_steps_by_id) & set(new_steps_by_id))):
            if (not isinstance(current.get('plan_revision_source'), str) or
                    not current['plan_revision_source'].strip()):
                errors.append('changed plan steps require plan_revision_source')
    if (not same_plan_identity and isinstance(old_plan, dict) and old_plan.get('presented') is True and
            (old_steps_by_id or new_steps_by_id) and
            (old_step_order != new_step_order or
             any(old_steps_by_id.get(ident, {}).get('action') != new_steps_by_id.get(ident, {}).get('action')
                 for ident in set(old_steps_by_id) | set(new_steps_by_id)))):
        if (not isinstance(current.get('plan_revision_source'), str) or
                not current['plan_revision_source'].strip()):
            errors.append('changed plan steps require plan_revision_source')
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
    old_scope = None
    new_scope = None
    old_baseline_scope = None
    new_baseline_scope = None
    if isinstance(old_goals, dict):
        old_scope = (old_goals.get('included'), old_goals.get('excluded'))
    if isinstance(new_goals, dict):
        new_scope = (new_goals.get('included'), new_goals.get('excluded'))
    old_baseline = previous.get('goal_scope_baseline')
    new_baseline = current.get('goal_scope_baseline')
    if isinstance(old_baseline, dict):
        old_baseline_scope = (old_baseline.get('included'), old_baseline.get('excluded'))
    if isinstance(new_baseline, dict):
        new_baseline_scope = (new_baseline.get('included'), new_baseline.get('excluded'))
    baseline_changed = (
        isinstance(old_baseline, dict) and
        old_baseline_scope != new_baseline_scope
    )
    goal_scope_changed = (
        (isinstance(old_goals, dict) and old_goals.get('presented') is True and
         (not isinstance(new_goals, dict) or old_scope != new_scope)) or
        baseline_changed
    )
    goal_evidence_changed = (
        isinstance(old_goals, dict) and isinstance(new_goals, dict) and
        old_goals.get('presented') is True and new_goals.get('presented') is True and
        old_goals.get('evidence') != new_goals.get('evidence')
    )
    old_local_goal_id = old_goals.get('local_goal_id') if isinstance(old_goals, dict) else None
    new_local_goal_id = new_goals.get('local_goal_id') if isinstance(new_goals, dict) else None
    goal_identity_changed = (
        isinstance(old_local_goal_id, str) and old_local_goal_id.strip() and
        (not isinstance(new_local_goal_id, str) or not new_local_goal_id.strip() or
         old_local_goal_id != new_local_goal_id)
    )
    if goal_scope_changed or goal_evidence_changed or goal_identity_changed:
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
    if goal_scope_changed or goal_evidence_changed:
        if isinstance(old_gates, dict) and isinstance(new_gates, dict):
            for name in ('goals', 'execution'):
                if old_gates.get(name) and old_gates.get(name) == new_gates.get(name):
                    errors.append('changed goals require reviewing old ' + name + ' authorization')
    confirmed_scope_change = (goal_scope_changed and isinstance(old_gates, dict) and
                              isinstance(new_gates, dict) and
                              has_new_source(new_gates.get('goals'), old_gates.get('goals')))
    errors.extend(validate_operation_transition(previous, current, confirmed_scope_change))
    return errors


def discussion_decisions(s):
    decisions = s.get('decisions')
    if not isinstance(decisions, list):
        return {}
    fields = ('subject', 'status', 'value', 'source', 'implementation', 'verification', 'depends_on', 'business_context')
    return {
        item['id']: tuple(item.get(field) for field in fields)
        for item in decisions
        if isinstance(item, dict) and isinstance(item.get('id'), str)
        and item.get('blocks_plan') is not False
    }


def discussion_ready(s):
    return (s.get('coverage_checked') is True and isinstance(s.get('decisions'), list) and
            not any(decision[1] == 'pending' for decision in discussion_decisions(s).values()))


def discussion_transition_waiting(s):
    source = s.get('discussion_closure_question_source')
    return (s.get('status') == 'wait_user' and
            isinstance(source, str) and bool(source.strip()) and s.get('wait_evidence') == source)


def discussion_transition_confirmed(s):
    question = s.get('discussion_closure_question_source')
    answer = s.get('discussion_closure_source')
    return (s.get('discussion_closed') is True and
            isinstance(question, str) and isinstance(answer, str) and
            bool(question.strip()) and bool(answer.strip()) and
            question.strip() != answer.strip())


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


def missing_goal_presentation(s):
    goals = s.get('goals')
    return s['plan']['presented'] is True and (
        not isinstance(goals, dict) or goals.get('presented') is not True
    )


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
        elif unrelated_closed(frame) and not has_return_consent(frame):
            point = frame['resume_point']
            if frame.get('return_question_source'):
                result.update(action='wait_interruption', status='wait_user',
                              reason='等待用户明确同意返回，保留原待答点')
            else:
                pending = point['next_action']
                evidence = point.get('wait_evidence')
                if point['status'] == 'wait_user' and evidence.strip().endswith(('？', '?')):
                    pending = evidence.strip().rstrip('？?')
                destination = frames[-2]['request'] if len(frames) > 1 else '原任务'
                result.update(action='ask_return_to_main',
                              question=f'是否回到{destination}，继续「{pending}」？')
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
    if (status == 'blocked' and isinstance(independent, str) and independent.strip() and
            independent_action_allowed(s)):
        return {'action': 'continue_local', 'next_action': independent, 'blocked_reason': s['wait_reason']}
    if (status == 'blocked' and s['phase'] in ('planning', 'goals') and
            missing_goal_presentation(s) and
            s.get('local_only') is not True):
        return {'action': 'continue_local', 'plan_supplement': True,
                'next_action': '必须先核对计划确认、待决事项及当前展示范围，再按结果行动。允许时一起展示计划和目标，否则必须处理缺口或等待。',
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
            if (s.get('independent_action') and
                    (not needs_execution_gates or
                     (gates.get('execution') and gates.get('subagents'))) and
                    independent_action_allowed(s)):
                result['independent_action'] = s['independent_action']
            checks = [op.get('reference') for op in s.get('operations', []) if isinstance(op, dict) and op.get('status') in ('running', 'unknown') and op.get('independent_of_wait') is True]
            if checks:
                result['independent_checks'] = checks
        return result
    checking_operation = any(
        isinstance(operation, dict) and operation.get('blocks_next') is True and
        operation.get('status') in ('unknown', 'running')
        for operation in s.get('operations', [])
    )
    for operation in s.get('operations', []):
        if not isinstance(operation, dict) or operation.get('blocks_next') is not True:
            continue
        if operation.get('status') in ('unknown', 'running'):
            return {'action': 'check_operation', 'reference': operation.get('reference')}
        if operation.get('status') == 'failed':
            return {'action': 'handle_operation_failure', 'reference': operation.get('reference')}
    if accepting_superseded(s):
        if s.get('local_only') and s.get('local_done'):
            return {'action': 'local_complete' if s.get('coverage_checked') else 'check_coverage'}
        return {'action': 'continue_local' if s.get('local_only') else 'continue_current_phase',
                'next_action': '必须将只读核对限定在本轮范围内的既有证据。开始新业务动作前必须另行满足有效的执行入口条件。'}
    if (s['phase'] == 'execution' and s.get('status') == 'continue' and
            not checking_operation and s.get('execution_begun') is not True):
        return {'action': 'begin_execution', 'next_action': '必须取得执行入口回执后再继续'}
    if (s['phase'] == 'execution' and s.get('status') == 'continue' and
            not s.get('local_only')):
        steps = s.get('plan', {}).get('steps', [])
        if isinstance(steps, list):
            current = next((step for step in steps if isinstance(step, dict) and step.get('status') == 'in_progress'), None)
            if current is not None:
                return {'action': 'continue_step', 'step_id': current.get('id'),
                        'next_action': current.get('action')}
            blocked = next((step for step in steps if isinstance(step, dict) and step.get('status') == 'blocked'), None)
            if blocked is not None:
                return {'action': 'step_blocked', 'step_id': blocked.get('id'),
                        'reason': blocked.get('reason')}
            pending = next((step for step in steps if isinstance(step, dict) and step.get('status') == 'pending'), None)
            if pending is not None:
                return {'action': 'start_step', 'step_id': pending.get('id'),
                        'next_action': pending.get('action')}
            if (not s.get('local_only') and steps and
                    all(isinstance(step, dict) and step.get('status') == 'done' for step in steps)):
                return {'action': 'steps_complete', 'next_action': '必须进入验证与审查'}
    if s.get('local_only') and s.get('local_done'):
        if s.get('coverage_checked') is not True:
            return {'action': 'check_coverage'}
        return {'action': 'local_complete'}
    if s.get('local_only'):
        steps = s.get('plan', {}).get('steps', [])
        if (steps and all(isinstance(step, dict) and step.get('status') == 'done' for step in steps)):
            return {'action': 'steps_complete', 'next_action': '必须进入验证与审查'}
        return {'action': 'continue_local', 'next_action': s['next_action']}
    if (s.get('scope_limited') is True and s.get('coverage_checked') is True and
            s.get('plan_requested') is not True and
            not missing_goal_presentation(s)):
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
        if missing_goal_presentation(s):
            return {'action': 'present_plan'}
        if s.get('plan_required', True) and (s['phase'] == 'discussion' or not s['plan']['presented']):
            return {'action': ('present_plan' if discussion_transition_confirmed(s)
                               else 'request_plan_transition')}
    if s['phase'] == 'analysis':
        return {'action': 'continue_analysis', 'next_action': '必须完成分析后再进入讨论'}
    return {'action': 'continue_current_phase', 'next_action': s['next_action']}


def begin_execution(s, previous=None):
    """Return the one-time execution receipt only after the full entry gate passes."""
    if not isinstance(s, dict):
        return {'ok': False, 'errors': ['checkpoint must be an object']}
    errors = validate(s)
    scope = s.get('execution_scope')
    if isinstance(scope, dict) and 'subagent_policy' not in scope:
        errors.append('begin requires execution_scope.subagent_policy')
    if previous is None:
        errors.append('previous state required for execution begin')
    if previous is not None:
        errors.extend(validate_transition(previous, s))
    if s.get('phase') != 'execution':
        errors.append('begin requires phase execution')
    if s.get('status') != 'continue':
        errors.append('begin requires status continue')
    if s.get('execution_begun') is True:
        errors.append('execution already begun; reuse the existing receipt or start a new task')
    if s.get('scope_limited') is True or s.get('local_only_read_only') is True:
        errors.append('begin is blocked by the current scope limit')
    renewing = isinstance(previous, dict) and previous.get('execution_begun') is True
    if renewing:
        renewing = (
            previous.get('phase') in ('execution', 'verification', 'review') and
            previous.get('status') != 'complete' and not validate(previous) and
            previous.get('execution_receipt') == execution_receipt(previous) and
            has_new_source(s.get('execution_reset_source'), None)
        )
        if not renewing:
            errors.append('renewed begin requires a valid previous execution and reset source')
        else:
            errors.extend(validate_execution_confirmation(previous, s, renewing=True))
    elif isinstance(previous, dict):
        errors.extend(validate_execution_confirmation(previous, s, renewing=False))
    plan = s.get('plan')
    steps = plan.get('steps', []) if isinstance(plan, dict) else []
    if not isinstance(steps, list):
        steps = []
    progressed = [step for step in steps if isinstance(step, dict) and
                  step.get('status') in ('done', 'in_progress')]
    if progressed:
        if not renewing:
            errors.append('begin with progressed steps requires a valid previous execution and reset source')
        else:
            old_steps = {step['id']: step for step in previous['plan']['steps']}
            for step in progressed:
                old = old_steps.get(step.get('id'), {})
                if (old.get('action') != step.get('action') or
                        old.get('status') != step.get('status') or
                        old.get('evidence') != step.get('evidence')):
                    errors.append('renewed begin must preserve evidenced progress: ' + str(step.get('id')))
    if not errors:
        routed = route(s)
        if routed.get('action') != 'begin_execution':
            errors.append('begin blocked by next action: ' + str(routed.get('action')))
    if errors:
        return {'ok': False, 'action': 'repair_state', 'errors': errors}
    return {
        'ok': True,
        'action': 'begin_execution',
        'execution_receipt': execution_receipt(s),
        'step_ids': [
            step.get('id') for step in s.get('plan', {}).get('steps', [])
            if isinstance(step, dict)
        ],
        'scope': 'structure_only',
    }


def validate_execution_confirmation(previous, current, *, renewing):
    """Require the already displayed content followed by a separate user decision."""
    if not renewing and (previous.get('phase') not in ('planning', 'goals') or
            any(not isinstance(previous.get(key), dict) or
                previous[key].get('presented') is not True for key in ('plan', 'goals'))):
        return ['first begin requires a previous state with plan and goals already presented']
    old = execution_authorization_payload(previous)
    new = execution_authorization_payload(current)
    # A local tracking ID can first be assigned after the user authorizes execution.
    del old['goals']['local_goal_id']
    del new['goals']['local_goal_id']
    errors = []
    changed_content = [key for key in ('plan', 'goals') if old[key] != new[key]]
    if not renewing and changed_content:
        errors.append('first begin requires the same plan and goals as previously presented')
    if renewing:
        for key in changed_content:
            if not has_new_source(new[key]['evidence'], old[key]['evidence'], normalize_spacing=True):
                errors.append('renewed begin requires new presentation evidence for changed ' + key)
        changed_scope = any(
            {item for item in old['execution_scope'][key] if isinstance(item, str)} !=
            {item for item in new['execution_scope'][key] if isinstance(item, str)}
            for key in ('allowed_paths', 'allowed_actions')
            if isinstance(old['execution_scope'].get(key), list) and
            isinstance(new['execution_scope'].get(key), list)
        )
        if not changed_scope and not changed_content:
            return errors
        if changed_scope and 'plan' not in changed_content:
            errors.append('renewed begin requires new plan presentation for changed execution scope')
    old_gates = old['gates'] if isinstance(old['gates'], dict) else {}
    new_gates = new['gates'] if isinstance(new['gates'], dict) else {}
    earlier_sources = ([old_gates.get('execution')] if renewing else
                       [*old_gates.values(), previous.get('plan_request_source'),
                        previous.get('discussion_closure_source')])
    earlier_sources.extend(new[key][field] for key in ('plan', 'goals')
                           for field in ('evidence', 'presentation_id'))
    if any(not has_new_source(new_gates.get('execution'), source, normalize_spacing=True)
           for source in earlier_sources):
        errors.append('begin requires a new user execution confirmation after presentation')
    return errors


def discussion_final_line(reply):
    lines = [line.strip() for line in reply.splitlines() if line.strip()]
    return lines[-1] if lines else ''


def validate_plan_final(state, reply, payload, routed):
    explicit = payload.get('formal_plan') is True or 'plan_coverage' in payload
    phase = state.get('phase') if isinstance(state, dict) else None
    if phase not in ('planning', 'goals'):
        return ['formal plan draft requires planning or goals phase'] if explicit else []

    action = routed['action']
    supplement = routed.get('plan_supplement') is True
    if action != 'present_plan' and not supplement and not explicit:
        return []
    revision = (action == 'continue_current_phase' and state['plan']['presented'] is True and
                not missing_goal_presentation(state))
    if not (action == 'present_plan' or supplement or revision):
        return ['formal plan draft conflicts with next action: ' + action]
    if supplement and (not discussion_ready(state) or any(
            op.get('blocks_next') is True and op['status'] in ('running', 'unknown', 'failed')
            for op in state.get('operations', []))):
        return ['formal plan supplement has pending decisions, unchecked coverage, or a blocking operation']
    return validate_plan_coverage(reply, payload.get('plan_coverage'))


def validate_plan_coverage(reply, requirements):
    """Check that the source-derived requirements have an actionable test in the draft."""
    if not isinstance(requirements, list) or not requirements:
        return ['formal plan requires a nonempty plan_coverage list']
    paragraphs = [' '.join(part.split()) for part in re.split(r'\n\s*\n', reply)]
    errors = []
    for index, requirement in enumerate(requirements):
        label = f'plan_coverage[{index}]'
        if not isinstance(requirement, dict) or any(
                not isinstance(requirement.get(field), str) or not requirement[field].strip()
                for field in ('source', 'trigger', 'expected')):
            errors.append(label + ' requires source, trigger, and expected')
            continue
        trigger = ' '.join(requirement['trigger'].split())
        expected = ' '.join(requirement['expected'].split())
        if trigger == expected or not any(
                trigger in paragraph and expected in paragraph for paragraph in paragraphs):
            errors.append(f'{label} ({requirement["source"]}) is missing a trigger or expected result in the draft')
    return errors


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
        'tool_wait': TOOL_WAIT_REVIEW_CHECKS,
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


def validate_choice_basis(basis, decisions):
    resolved = {item['id']: item.get('value') or item.get('subject') for item in decisions
                if isinstance(item, dict) and isinstance(item.get('id'), str)
                and item.get('status') in ('decided', 'delegated', 'excluded') and item.get('source')}
    if not resolved and isinstance(basis, dict) and set(basis) == {'no_material_choice_reason'}:
        reason = basis['no_material_choice_reason']
        if isinstance(reason, str) and reason.strip():
            return []
    if not isinstance(basis, list) or not basis:
        return ['plan transition requires choice_basis for material choices or a reason none exist']
    cited = set()
    for item in basis:
        if not isinstance(item, dict) or not isinstance(item.get('choice'), str) or not item['choice'].strip():
            return ['choice_basis requires a specific choice']
        ident = item.get('decision_id')
        if not isinstance(ident, str) or resolved.get(ident) != item['choice']:
            return ['choice_basis requires a resolved decision with a source']
        cited.add(ident)
    if cited != resolved.keys():
        return ['choice_basis must cover all resolved decisions']
    return []


def mermaid_text(value):
    return ''.join(char if char.isalnum() or char == ' ' else f'#{ord(char)};' for char in value)


def closure_overview(rows, decisions, history=()):
    """Render the discussion path, its resolved questions, and the requirement table."""
    graph = ['讨论图', '```mermaid', 'flowchart TD',
             'goal["目标确认"] --> discuss["讨论取舍"]']
    table = ['要求表', '| 你确认的要求 | 当前做法或待决问题 | 怎么验 | 状态 |',
             '| --- | --- | --- | --- |']
    statuses = {'confirmed': '已确认', 'decided': '已决定', 'delegated': '已落实委托', 'excluded': '已排除'}
    nodes = {row['id']: f'q{i}' for i, row in enumerate(decisions, 1) if 'id' in row}
    parent = 'discuss'
    for index, decision in enumerate(decisions, 1):
        subject = mermaid_text(decision['subject'])
        graph.append(f'{parent} --> q{index}["{subject}（{statuses[decision["status"]]}）"]')
        parent = f'q{index}'
    graph.extend([f'{parent} --> review["逐项核对"]',
                  'review --> wait["等待收口（当前位置：等待用户同意）"]',
                  'wait -->|用户同意后| plan["计划目标"]'])
    for index, entry in enumerate(history, 1):
        origin = nodes.get(entry['origin'], entry['origin'])
        label = mermaid_text(entry['request'])
        if entry['relation'] == 'unrelated':
            label += '（无意义分支（与当前目标无关））'
            graph.append(f'b{index}["{label}"]')
        else:
            graph.append(f'{origin} -.-> b{index}["{label}"]')
            target = nodes.get(entry['target'], entry['target'])
            graph.append(f'b{index} -->|"{mermaid_text(entry["impact"])}"| {target}')
    graph.append('```')
    for _, label, action, check, status, _ in rows:
        cells = [label, action, check, statuses[status]]
        table.append('| ' + ' | '.join(cell.replace('|', r'\|') for cell in cells) + ' |')
    return graph + table


def validate_closure_reply(reply, handoff, state, recorded_graph=None):
    """Bind every visible requirement to its confirmed wording and approach evidence."""
    review = handoff.get('semantic_review')
    if not isinstance(review, dict):
        return ['closure requires a semantic review']
    decisions = state.get('decisions', [])
    requirements = state.get('confirmed_requirements', [])
    if not isinstance(requirements, list) or not all(isinstance(row, dict) for row in requirements):
        return ['confirmed_requirements must be a list of records']
    resolved = [row for row in decisions if isinstance(row, dict)
                and row.get('status') in ('decided', 'delegated', 'excluded')]
    items = [(row, 'confirmed') for row in requirements] + [(row, row['status']) for row in resolved]
    lines = [line.strip() for line in reply.splitlines() if line.strip()]
    if lines and lines[0] == '**任务驱动 · 讨论阶段**':
        lines.pop(0)
    plan = state.get('plan')
    plan_presented = isinstance(plan, dict) and plan.get('presented') is True
    overview = contains_internal_overview(reply)
    strict = review.get('reviewer') == 'main' or overview or bool(requirements and not resolved)
    if not items and (strict or not plan_presented):
        return ['first closure requires sourced confirmed requirements or resolved decisions']

    rows = []
    identifiers = set()
    expected = []
    for item, status in items:
        ident = item.get('id')
        value = item.get('value') or item.get('subject')
        action, check = item.get('implementation'), item.get('verification')
        if not all(isinstance(part, str) and part.strip() and len(part.splitlines()) == 1
                   for part in (ident, value, action, check)):
            return ['closure requires an id, requirement, implementation and verification on each record']
        if ident in identifiers:
            return ['closure record ids must be unique']
        identifiers.add(ident)
        sources = [item.get('source'), item.get('detail_source'), value]
        if status == 'confirmed':
            constraint = item.get('constraint_source')
            if (not isinstance(item.get('source'), str) or value not in item['source']
                    or not isinstance(constraint, str) or action not in constraint):
                return ['confirmed requirement needs its wording and unique implementation in their respective sources']
            sources.append(constraint)
        if strict or status == 'confirmed':
            if not all(any(isinstance(source, str) and part in source for source in sources)
                       for part in (action, check)):
                return ['implementation and verification need supporting record excerpts']
        dependencies = item.get('depends_on', [])
        if overview and (not re.fullmatch(r'[\w.-]+', ident) or not isinstance(dependencies, list)
                         or not all(isinstance(key, str) and key != ident for key in dependencies)):
            return ['overview needs stable ids and a list of prerequisite record ids']
        label = value
        if 'business_context' in item:
            context = item['business_context']
            if (not isinstance(context, str) or not context.strip() or len(context.splitlines()) != 1
                    or not any(isinstance(source, str) and context in source for source in sources)):
                return ['business_context must quote a distinguishing context from the same record']
            label = f'{value}（{context}）'
        rows.append((ident, label, action, check, status, dependencies))
        expected.append(f'{label}：{action}，核验时{check}。')

    body = lines[:-1]
    if overview:
        if any(key not in identifiers for row in rows for key in row[-1]):
            return ['overview dependency must reference a displayed requirement']
        if len({' '.join(row[1].split()) for row in rows}) != len(rows):
            return ['overview needs distinct business labels; qualify matching names with business_context']
        if any(not isinstance(row.get('subject'), str) or not row['subject'].strip() for row in resolved):
            return ['discussion graph branches require a decision subject']
        if any(not re.fullmatch(r' {0,3}```(?:mermaid)?[ \t]*', line)
               for line in reply.splitlines() if line.strip() in ('```mermaid', '```')):
            return ['discussion graph requires a Markdown fenced Mermaid block']
        history = state.get('branch_history', [])
        graph_nodes = {row['id'] for row in resolved} | {'discuss', 'review'}
        if any(entry['origin'] not in graph_nodes or entry.get('target', 'review') not in graph_nodes
               for entry in history):
            return ['branch history must reference displayed discussion nodes']
        prefix = closure_overview(rows, resolved, history)
        table_start = prefix.index('要求表')
        table = prefix[table_start:]
        graph = prefix[:table_start]
        if recorded_graph is not None:
            graph = ['讨论图', '```mermaid', *(line.strip() for line in recorded_graph.splitlines() if line.strip()), '```']
        # Locate each whole block rather than assuming the overview starts the reply.
        # Explanations remain in body for the full-draft semantic review below.
        spans = []
        for title, marker, block in (
                ('讨论图', '```mermaid', graph[1:]),
                ('要求表', table[1], table[1:])):
            starts = [index for index, line in enumerate(body)
                      if line == marker or title == '要求表' and table_cells(line) == REQUIREMENT_COLUMNS]
            if len(starts) > 1 or body.count(title) > 1 or (title in body and not starts):
                return ['task overview requires one complete block of each requested kind']
            if not starts:
                continue
            start = starts[0]
            if title == '讨论图':
                end = next((index + 1 for index in range(start + 1, len(body))
                            if body[index] == '```'), len(body))
            else:
                end = start + 1
                while end < len(body) and body[end].startswith('|'):
                    end += 1
            if body[start:end] != block:
                return ['task overview must show the graph and table from the same closure records']
            if start and body[start - 1] == title:
                start -= 1
            spans.append((start, end))
        if not spans:
            return ['task overview requires a complete graph or requirement table']
        body = [line for index, line in enumerate(body)
                if not any(start <= index < end for start, end in spans)]
        remaining = [re.sub(r'^(?:>[ \t]*)+', '', line) for line in body]
        if any(line in ('讨论图', '要求表') or table_cells(line) == REQUIREMENT_COLUMNS or
               re.match(r'^(?:flowchart|graph)\s+(?:TD|TB|LR|RL|BT)\b', line)
               for line in remaining):
            return ['task overview contains an unmatched graph or table']
    body = [line.removeprefix('- ') for line in body]
    if strict and (not lines or lines[-1] != '是否结束讨论并开始展示正式计划和验收目标？'):
        return ['self-reviewed closure requires a separate closure question']
    for line in expected:
        if body.count(line) != 1:
            return ['closure must show each recorded implementation and verification exactly once']
        body.remove(line)
    if body:
        digest = hashlib.sha256(reply.encode('utf-8')).hexdigest()
        if (review.get('reviewed_reply_sha256') != digest or
                not isinstance(review.get('checks'), dict) or
                review['checks'].get('no_new_material_choices') is not True):
            return ['additional closure prose requires a full-draft semantic review with no new material choices']
    if review.get('reviewer') == 'independent' or (
            requirements and all(row['status'] == 'excluded' for row in resolved)):
        return []
    return validate_selected_approach(handoff.get('approach_basis'), resolved)


def validate_selected_approach(approach, decisions):
    """Verify a material choice against the original decision evidence."""
    if not isinstance(approach, dict):
        return ['self-reviewed closure requires approach_basis for the actual solution']
    decision = next((item for item in decisions if isinstance(item, dict)
                     and item.get('id') == approach.get('decision_id')
                     and item.get('status') in ('decided', 'delegated')), None)
    quote = approach.get('source_quote')
    if (not decision or not isinstance(quote, str) or not quote.strip()
            or not isinstance(decision.get('source'), str) or quote not in decision['source']):
        return ['approach_basis must cite the selected approach and its source quotation']
    if decision['status'] == 'decided' and (not isinstance(decision.get('value'), str) or decision['value'] not in quote):
        return ['selected approach must occur in the cited decision wording']
    return []


def validate_discussion_final(s, reply, handoff, recorded_graph=None):
    """Validate a discussion question, user-scoped stop, or actual tool wait."""
    if not isinstance(s, dict):
        return []
    if s.get('phase') == 'discussion' and isinstance(reply, str) and contains_internal_overview(reply):
        source = handoff.get('overview_request_source') if isinstance(handoff, dict) else None
        if not isinstance(source, str) or not source.strip():
            return ['showing the discussion diagram or requirement table requires an explicit user request']
    frames = s.get('interruptions')
    if isinstance(frames, list) and frames and not validate_interruptions(s) and unrelated_closed(frames[-1]):
        action = route(s)
        if action['action'] == 'ask_return_to_main':
            lines = reply.rstrip().splitlines()
            body = [line.strip() for line in lines[:-1] if line.strip()]
            if body[:1] == ['**任务驱动 · 讨论阶段**']:
                body.pop(0)
            if (not body or
                    discussion_final_line(reply) != action['question'] or
                    count_questions_outside_code(reply) != 1):
                return ['closed unrelated branch requires only the return question after its result']
            return []
        if action['action'] == 'wait_interruption':
            return ['wait for explicit return consent before a main-task handoff']
    if s.get('phase') == 'planning' and discussion_transition_waiting(s):
        return ['first formal plan presentation requires confirmed discussion transition']
    if (s.get('phase') == 'planning' and s.get('plan_required', True) and
            isinstance(s.get('plan'), dict) and s['plan'].get('presented') is False and
            route(s).get('action') != 'present_plan'):
        return ['first formal plan presentation requires confirmed discussion transition']
    if s.get('phase') != 'discussion':
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
    kind = handoff.get('kind')
    if blocking_operations and (kind != 'tool_wait' or any(
            isinstance(operation, dict) and operation.get('blocks_next') is True and
            operation.get('status') == 'failed' for operation in s.get('operations', []))):
        return ['discussion final blocked by unresolved operation: ' + ', '.join(blocking_operations)]
    if kind not in ('decision', 'plan_transition', 'waived', 'tool_wait'):
        return ['discussion_handoff.kind must be decision, plan_transition, waived, or tool_wait']
    question_count = count_questions_outside_code(reply)
    waiver = s.get('discussion_question_waiver_source')
    routed = route(s)
    route_action = routed.get('action')
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
    if kind == 'tool_wait':
        if s.get('status') != 'wait_tool' or routed.get('action') != 'wait_tool':
            return review_errors + ['discussion tool wait requires the current wait_tool route']
        if any(isinstance(item, dict) and item.get('status') == 'pending' and
               item.get('blocks_plan', True) is not False for item in s.get('decisions', [])):
            review_errors.append('discussion tool wait cannot bypass pending decisions')
        draft_action = pending_plan_request_action(s)
        if draft_action and s.get('scope_limited') is True and s.get('scope_limited_source') == s.get('plan_request_source'):
            wait_review = validate_semantic_review(
                handoff.get('semantic_review'), kind, extra_checks=('formal_plan_only_wait',))
            if not wait_review:
                draft_action = None
            else:
                review_errors = wait_review
        if routed.get('independent_action') or routed.get('independent_checks') or draft_action:
            review_errors.append('discussion tool wait cannot bypass available work or a pending plan request')
        if s.get('coverage_checked') is not True:
            review_errors.append('discussion final requires coverage_checked before handoff')
        if question_count != 0:
            review_errors.append('discussion tool wait final must not add a question')
        return review_errors
    if kind == 'waived':
        if s.get('scope_limited') is True:
            source = s.get('scope_limited_source')
            if not isinstance(source, str) or not source.strip():
                return ['scope limited source required']
            draft_only = (route_action in ('present_incomplete_plan', 'resolve_pending') and
                          s.get('coverage_checked') is True and
                          source == s.get('plan_request_source') and
                          s.get('plan_requested') is True)
            if draft_only:
                review_errors = validate_semantic_review(
                    handoff.get('semantic_review'), kind,
                    extra_checks=('draft_only_scope', 'incomplete_plan_delivered'))
            elif route_action not in ('scope_complete', 'local_complete', 'paused', 'complete'):
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
        waiting_for_answer = route_action == 'wait_user' and discussion_transition_waiting(s)
        if not waiting_for_answer:
            errors.extend(validate_closure_reply(reply, handoff, s, recorded_graph))
            errors.extend(validate_choice_basis(handoff.get('choice_basis'), s.get('decisions', [])))
        if waiting_for_answer and (routed.get('independent_action') or routed.get('independent_checks')):
            errors.append('discussion plan transition cannot bypass available independent work')
        if route_action != 'request_plan_transition' and not waiting_for_answer:
            errors.append('discussion plan transition conflicts with next action: ' + str(route_action))
    return errors


STATE_REPAIR_HINTS = {
    'first formal plan presentation requires confirmed discussion transition': (
        'discussion_closure_question_source', '必须保持讨论阶段，按收口条件核对实际发出的问题和用户对该问题的明确肯定答复。'
        '满足收口条件但尚未提问时，必须先实际询问。已问但尚无明确肯定答复时，禁止进入计划阶段。未答时必须等待。'
        '必须引用实际发出的问题和实际收到的对应答复。'),
    'discussion transition answer must match the preceding question': (
        'discussion_closure_question_source', '必须引用上一讨论状态中实际待答的收口问题，以及用户本次对该问题的明确肯定答复。'),
    'discussion transition must be reconfirmed after a material change': (
        'discussion_closed', '必须接回讨论并核对变化影响。原收口答复只覆盖原决定，禁止用于本次收口。当前方案谈妥后必须重新询问是否结束讨论，并等待对应的明确肯定答复。'),
    'formal plan display requires the preceding discussion or presentation state': (
        'previous', '首次展示必须传入实际发出收口问题后的待答状态。补齐旧计划的目标时，必须传入有真实展示来源的旧状态。'),
    'a previously presented formal plan must retain its presentation state without a revision source': (
        'plan.presented', '必须保留真实的旧计划和展示来源。用户确实要求撤换旧计划时，'
        '必须保留前态并引用实际修订消息，再按影响核对旧确认。'),
    'execution_scope.source required': (
        'execution_scope.source', '必须引用用户明确授权本次执行范围的消息。只有计划或目标内容确认时，必须保持未授权状态。'),
    'goal_scope_baseline required for previous goal state': (
        'previous.goal_scope_baseline', '必须从上一轮目标快照恢复当时的 included 和 excluded。'
        '若手上的 previous 并非那一轮快照，必须先核对记录。禁止用当前目标填旧快照。'),
    'changed goals require superseded_goals or stale host goal record': (
        'goals', '必须对照上一状态的目标、展示来源及目标标识。仅有取证进展时，必须将目标字段的变更限定在 evidence_map。'
        '目标确实变更时，必须按实际范围和确认来源记录替代关系，并按现场填写宿主同步状态。'),
    'wait_user requires reference to already presented question': (
        'wait_evidence', '必须引用已经实际发出的那道待答问题。拟发问题必须先走提问交接，禁止在问题发出前记为等待用户。'),
    'resuming paused task requires source': (
        'resume_source', '必须核对用户是否明确恢复当前任务。已明确恢复时必须引用该消息。只有反馈或插问时，必须保持原任务暂停。'),
    'changed goal tracking requires a new confirmation source': (
        'goal_tracking_confirmation_source', '必须核对当前目标跟踪方式是否实际变更。未变时必须沿用有效设置。'
        '确实改用降级方式时，必须先取得并引用对应确认。'),
    'plan step action cannot change without a new plan': (
        'plan.steps', '必须核对动作变化对应的计划修订。只有状态或证据变化时，必须沿用原动作。'
        '动作确实变更时，必须用实际修订来源更新计划，并保留未受影响的步骤进度。'),
    'additional closure prose requires a full-draft semantic review with no new material choices': (
        'discussion_handoff.semantic_review',
        '完整正文复核后，在 semantic_review.checks 内填写 no_new_material_choices:true，'
        '不是 semantic_review 的直接字段。reviewed_reply_sha256 则直接放在 semantic_review 下，'
        '值为当前完整 draft_reply 的 UTF-8 SHA-256；正文改变须重新复核并计算哈希。'
        '发现新增实质选择时不得填写通过，须回到讨论。'),
    'closure must show each recorded implementation and verification exactly once': (
        'draft_reply', '每项记录在正文单列一次“原值：做法，核验时验法。”，沿用记录措辞。'
        '核对遗漏、重复或改写，正文修改后重新语义复核并计算已有哈希。'),
    'approach_basis must cite the selected approach and its source quotation': (
        'discussion_handoff.approach_basis.source_quote',
        'decision_id 必须指向已决定或已落实委托的记录；source_quote 必须逐字摘自该记录的 source。'
        '若 source 仅保存用户原话的一段，引用这一段，不能改用未保存在其中的整条消息。'
        '不得编造或扩写用户来源来通过检查。'),
    'self-reviewed closure requires approach_basis for the actual solution': (
        'discussion_handoff.approach_basis', '必须是单个对象 {decision_id, source_quote}，不是数组。'
        'choice_basis 才是覆盖各项选择的数组。approach_basis 选实际采用做法的一条记录，'
        '填写其 decision_id 与原决定来源摘录 source_quote。'
        '采用依据必须覆盖做法与委托范围，不能用调研事实冒充采用决定。'),
    'completion evidence required': (
        'completion_evidence', '必须引用已发生的交付或完成证据。仍待在回复中交付的内容，必须先实际交付，再按实际事件同步。'),
}


def changed_goal_ids(previous, current):
    if not isinstance(previous, dict) or not isinstance(current, dict):
        return []

    def items_by_id(record):
        if not isinstance(record, dict):
            return {}
        return {
            item['id']: (group, item)
            for group in ('included', 'excluded')
            for item in (record.get(group) if isinstance(record.get(group), list) else [])
            if isinstance(item, dict) and isinstance(item.get('id'), str)
        }

    affected = set()
    for field in ('goals', 'goal_scope_baseline'):
        before_record, after_record = previous.get(field), current.get(field)
        if not isinstance(before_record, dict) or not isinstance(after_record, dict):
            continue
        before, after = items_by_id(before_record), items_by_id(after_record)
        affected.update(ident for ident in before.keys() | after.keys()
                        if before.get(ident) != after.get(ident))
    return sorted(affected)


def add_error_diagnostics(result, state, previous=None):
    """Explain selected input errors without changing validation or routing."""
    diagnostics = []
    errors = [(error, 'errors') for error in result.get('errors', [])]
    errors += [(error, 'original_state_errors') for error in result.get('original_state_errors', [])]
    for error, source in errors:
        detail = None
        if error == 'invalid phase':
            detail = {
                'field': 'phase',
                'actual': state.get('phase') if isinstance(state, dict) else None,
                'allowed': sorted(PHASES),
                'hint': '必须按实际环节填写合法值。禁止为修正字段而自动转换或推进阶段。',
            }
        elif error in ('presented plan requires evidence', 'presented goals require evidence'):
            field = 'plan' if error == 'presented plan requires evidence' else 'goals'
            detail = {
                'field': field + '.evidence',
                'hint': '准备展示不等于已经展示。展示来源必须引用实际交付的可核实消息。'
                        '尚未展示时必须保留真实状态，按 next 返回动作展示。禁止填未来回复来通过检查。'
                        '已经展示时必须恢复其真实来源，禁止为绕过检查改成未展示。',
            }
        elif error == 'implementation and verification need supporting record excerpts':
            missing = []
            for group in ('confirmed_requirements', 'decisions'):
                records = state.get(group, []) if isinstance(state, dict) else []
                if not isinstance(records, list):
                    continue
                for index, item in enumerate(records):
                    if not isinstance(item, dict):
                        continue
                    if group == 'decisions' and item.get('status') not in ('decided', 'delegated', 'excluded'):
                        continue
                    sources = [item.get('source'), item.get('detail_source'),
                               item.get('value') or item.get('subject')]
                    if group == 'confirmed_requirements':
                        sources.append(item.get('constraint_source'))
                    for field in ('implementation', 'verification'):
                        value = item.get(field)
                        if isinstance(value, str) and value and not any(
                                isinstance(excerpt, str) and value in excerpt for excerpt in sources):
                            missing.append({'field': f'{group}[{index}].{field}',
                                            'record_id': item.get('id'), 'actual': value})
            detail = {
                'field': 'closure_records',
                'missing_excerpts': missing,
                'hint': '所列字段的完整措辞未出现在该条记录的 source、detail_source 或原值中。'
                        '按真实依据修正措辞，或在 detail_source 引用已形成方案的位置与原文；'
                        '确认要求也可依据 constraint_source。禁止为通过检查编造依据或用户确认。',
            }
        elif error in STATE_REPAIR_HINTS:
            field, hint = STATE_REPAIR_HINTS[error]
            detail = {'field': field, 'hint': hint}
            if error == 'changed goals require superseded_goals or stale host goal record':
                affected = changed_goal_ids(previous, state)
                if affected:
                    detail['changed_goal_ids'] = affected
        if detail is not None:
            if source == 'original_state_errors':
                detail['error_source'] = source
            diagnostics.append(detail)
    if diagnostics:
        result['diagnostics'] = diagnostics


def apply_state_changes(previous, changes):
    """Expand changes against a valid snapshot before running normal checks."""
    errors = validate(previous)
    if errors:
        raise ValueError('invalid previous state: ' + '; '.join(errors))
    if not isinstance(changes, list):
        raise ValueError('changes must be a list')
    state = deepcopy(previous)
    for index, change in enumerate(changes, 1):
        label = f'change {index}'
        if not isinstance(change, dict):
            raise ValueError(label + ' must be an object')
        setting = set(change) == {'path', 'value'}
        removing = set(change) == {'path', 'remove'} and change['remove'] is True
        if not (setting or removing):
            raise ValueError(label + ' requires path and either value or remove:true')
        path = change['path']
        if not isinstance(path, list) or not path:
            raise ValueError(label + ' requires a nonempty path')
        parent = state
        for depth, key in enumerate(path):
            last = depth == len(path) - 1
            if isinstance(parent, dict) and isinstance(key, str):
                if last and setting:
                    parent[key] = deepcopy(change['value'])
                elif key not in parent:
                    raise ValueError(f'{label} path does not exist at {path[:depth + 1]!r}')
                elif last:
                    del parent[key]
                else:
                    parent = parent[key]
            elif isinstance(parent, list) and type(key) is int and 0 <= key < len(parent):
                if not last:
                    parent = parent[key]
                elif setting:
                    parent[key] = deepcopy(change['value'])
                else:
                    raise ValueError(label + ' must replace the list to remove an element')
            else:
                raise ValueError(f'{label} invalid path at {path[:depth + 1]!r}')
    return state


def intake(payload):
    """Route a new request before a workflow checkpoint exists."""
    if not isinstance(payload, dict) or payload.keys() - {'goal', 'confirmation_source'}:
        raise ValueError('intake accepts only goal and confirmation_source for a new task')
    for field, value in payload.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError('intake requires nonempty text for ' + field)
    if 'goal' not in payload:
        if 'confirmation_source' in payload:
            raise ValueError('intake confirmation requires the goal it confirms')
        return {'action': 'ask_goal', 'question': '你想完成什么，做到什么程度算成功？'}
    if 'confirmation_source' not in payload:
        return {'action': 'confirm_understanding', 'question': f"我理解你的目标是「{payload['goal']}」，对吗？"}
    return {'action': 'continue_analysis', 'instruction': '按已确认目标进入 analysis 开展调查。'}


REQUIREMENT_COLUMNS = ['你确认的要求', '当前做法或待决问题', '怎么验', '状态']


def contains_internal_overview(reply):
    # Markdown quote prefixes change presentation, not the content of a pasted table or graph.
    text = re.sub(r'(?m)^[ \t]*(?:>[ \t]*)+', '', reply)
    if any(table_cells(line) == REQUIREMENT_COLUMNS for line in text.splitlines()):
        return True
    return bool(re.search(r'(?im)^[ \t]*(?:flowchart|graph)\s+(?:TD|TB|LR|RL|BT)\b', text)
                and any(marker in text for marker in ('当前位置', '讨论取舍', '讨论推进图', '等待收口')))


def has_main_edge(graph):
    # Remove labels before matching endpoints so arrows in business wording are never edges.
    syntax = re.sub(r'"[^"\n]*"', '', graph)
    syntax = re.sub(r'\[[^\]\n]*\]|\([^()\n]*\)|\{[^}\n]*\}|\|[^|\n]*\|', '', syntax)
    return any(edge[1] != edge[2] for edge in re.finditer(
        r'([\w-]+)[ \t]*-->[ \t]*([\w-]+)', syntax))


def table_cells(line):
    return [cell.strip() for cell in re.split(r'(?<!\\)\|', line.strip().strip('|'))]


def read_discussion_record(record, *, readback=None, decision_ids=()):
    fields = ('project', 'summary', 'turn_id', 'answer')
    if not isinstance(record, dict) or not all(
            isinstance(record.get(k), str) and record[k].strip() for k in fields):
        raise ValueError('discussion_record requires project, summary, turn_id and answer')
    root = Path(record['project']).resolve(strict=True)
    path = (root / record['summary']).resolve(strict=True)
    if not root.is_dir() or root not in path.parents or path.suffix.lower() != '.md' or not path.is_file():
        raise ValueError('summary must be a Markdown file within the current project')
    lines = path.read_text(encoding='utf-8').splitlines()
    ranges = record.get('readback_ranges', [])
    if not isinstance(ranges, list) or any(
            not isinstance(span, list) or len(span) != 2 or
            any(type(value) is not int for value in span) or
            not (1 <= span[0] <= span[1] <= len(lines)) for span in ranges):
        raise ValueError('readback_ranges requires inclusive integer line ranges within the summary')
    graphs, prose = [], []
    fence = None
    for line in lines:
        if fence:
            if re.fullmatch(r' {0,3}' + fence[0] + '{' + str(len(fence)) + r',}[ \t]*', line):
                fence = None
            elif in_graph:
                graphs[-1].append(line)
            continue
        opener = re.fullmatch(r' {0,3}(`{3,}|~{3,})(.*)', line)
        if opener:
            fence, info = opener.groups()
            in_graph = info.strip().lower() == 'mermaid'
            if in_graph:
                graphs.append([])
            prose.append('')
        else:
            prose.append(line)
    if fence or len(graphs) != 1:
        raise ValueError('summary requires one complete Mermaid discussion tree')
    graph = '\n'.join(line for line in graphs[0] if not line.lstrip().startswith('%%')).strip()
    if (not re.match(r'^flowchart\s+TD\s*$', graph.split('\n')[0]) or not has_main_edge(graph)
            or graph.count('当前位置') != 1 or not re.search(r'[\[({][^\]})\n]*当前位置[^\]})\n]*[\]})]', graph)):
        raise ValueError('discussion tree requires flowchart TD, a main path and one current node')
    headers = [i for i, line in enumerate(prose) if table_cells(line) == REQUIREMENT_COLUMNS]
    if len(headers) != 1:
        raise ValueError('summary requires one current four-column requirement table')
    start = headers[0]
    separator = table_cells(prose[start + 1]) if start + 1 < len(prose) else []
    if len(separator) != 4 or not all(re.fullmatch(r':?-{3,}:?', cell) for cell in separator):
        raise ValueError('invalid requirement table separator')
    referenced_decisions = set()
    index = start + 2
    while index < len(prose) and '|' in prose[index]:
        cells = table_cells(prose[index])
        if len(cells) != 4 or not all(cells):
            raise ValueError('each requirement row needs four nonempty cells')
        for ident in decision_ids:
            if re.search(r'(?<![\w-])' + re.escape(ident) + r'(?![\w-])', prose[index]):
                referenced_decisions.add(ident)
        index += 1
    if index == start + 2:
        raise ValueError('requirement table needs a current row')
    missing_nodes = sorted(ident for ident in referenced_decisions
                           if not re.search(r'(?<![\w-])' + re.escape(ident) + r'\s*[\[({]', graph))
    if missing_nodes:
        raise ValueError('requirement table references missing graph decision nodes: ' + ', '.join(missing_nodes))
    for label, field in [('本轮消息', 'turn_id'), ('本轮答复', 'answer')]:
        values = [line[len(label) + 1:].strip() for line in prose if line.startswith(label + '：')]
        if values != [record[field]]:
            raise ValueError(f'missing, duplicate or stale {field} in summary')
    if readback is not None:
        readback.extend({'start': start, 'end': end, 'text': '\n'.join(lines[start - 1:end])}
                        for start, end in ranges)
    return graph


def check_archived_branches(graph, history):
    """Check the recorded branch joins against the Markdown that will survive recovery."""
    if not history:
        return
    node_label = re.compile(r'([\w-]+)\[("[^"]*"|[^\]]*)\]')
    connection = re.compile(
        r'(?<![\w-])(?=([\w-]+)\s*(?:-->|-\.->)\s*(?:\|([^|]*)\|\s*)?([\w-]+))')
    nodes = set()
    edges = {}
    neighbors = {}
    for line in graph.splitlines():
        # Parse joins outside node captions, including chained joins on one line.
        nodes.update(label[1] for label in node_label.finditer(line))
        outline = node_label.sub(r'\1', line)
        for source, caption, target in connection.findall(outline):
            edges[source, target] = caption.strip('"')
            neighbors.setdefault(source, set()).add(target)
            neighbors.setdefault(target, set()).add(source)
    for entry in history:
        branch = entry['id']
        origin = entry['origin']
        if branch not in nodes or origin not in nodes:
            raise ValueError('archived branch and its original discussion node must remain in the tree')
        if entry['relation'] == 'related':
            target = entry['target']
            if ((origin, branch) not in edges or (branch, target) not in edges
                    or edges[branch, target] not in (entry['impact'], mermaid_text(entry['impact']))):
                raise ValueError('archived related branch requires its original fork, merge and impact')
        else:
            # A detached conversation can have several connected steps of its own.
            reached = {branch}
            frontier = [branch]
            while frontier:
                node = frontier.pop()
                unvisited = neighbors.get(node, set()) - reached
                reached.update(unvisited)
                frontier.extend(unvisited)
            if origin in reached:
                raise ValueError('an unrelated branch must remain disconnected from the main path')


def check_final_record(record, history=(), *, readback=None, decision_ids=()):
    if isinstance(record, dict) and 'read_only_source' in record and 'readback_ranges' in record:
        raise ValueError('readback_ranges requires a disk-backed discussion record')
    if isinstance(record, dict) and set(record) == {'read_only_source'}:
        source = record['read_only_source']
        if isinstance(source, str) and source.strip():
            return
        raise ValueError('read_only_source requires an explicit user instruction')
    graph = read_discussion_record(record, readback=readback, decision_ids=decision_ids)
    check_archived_branches(graph, history)
    return graph


def main():
    parser = argparse.ArgumentParser(description='Inspect workflow state or use record-check --help for a summary.')
    modes = ('intake', 'check', 'next', 'begin', 'final')
    if sys.argv[1:2] == ['record-check']:
        parser.prog += ' record-check'
        for flag in ('--project', '--summary', '--turn-id', '--answer'):
            parser.add_argument(flag, required=True)
        try:
            read_discussion_record(vars(parser.parse_args(sys.argv[2:])))
        except (OSError, RuntimeError, ValueError) as exc:
            print(json.dumps({'ok': False, 'errors': [str(exc)]}, ensure_ascii=False))
            return 1
        print(json.dumps({'ok': True}))
        return 0
    parser.add_argument('mode', choices=modes)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--state')
    source.add_argument('--json', dest='inline_json')
    parser.add_argument('--previous-state', help='Read the previous checkpoint from a JSON file for changes input')
    parser.add_argument('--emit-state', action='store_true', help='Include the checked current state on success')
    args = parser.parse_args()
    try:
        if args.inline_json is not None:
            payload = json.loads(args.inline_json)
        elif args.state == '-':
            payload = json.load(sys.stdin)
        else:
            with open(args.state, encoding='utf-8') as f:
                payload = json.load(f)

        if args.mode == 'intake':
            if args.previous_state or args.emit_state:
                raise ValueError('intake does not consume or emit workflow checkpoints')
            print(json.dumps(intake(payload), ensure_ascii=False))
            return 0

        if (isinstance(payload, dict) and 'changes' in payload and
                ('task_id' not in payload or 'state' in payload or 'previous' in payload)):
            if 'state' in payload or (args.previous_state is not None and 'previous' in payload):
                raise ValueError('changes require one previous state and no current state')
            if args.previous_state is not None:
                with open(args.previous_state, encoding='utf-8') as f:
                    previous = json.load(f)
            else:
                previous = payload.get('previous')
            if not isinstance(previous, dict):
                raise ValueError('changes require a previous checkpoint object')
            state = apply_state_changes(previous, payload['changes'])
            payload = {**payload, 'previous': previous, 'state': state}
        elif args.previous_state is not None:
            raise ValueError('--previous-state requires changes input')

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
            previous = payload.get('previous') if isinstance(payload, dict) else None
            state = payload.get('state') if isinstance(payload, dict) and 'state' in payload else payload
            draft_reply = None
            discussion_handoff = None
        if args.mode == 'begin':
            result = begin_execution(state, previous)
            add_error_diagnostics(result, state, previous)
            if args.emit_state and result.get('ok'):
                result['state'] = state
            print(json.dumps(result, ensure_ascii=False))
            return 0 if result.get('ok') else 1
        previous_required = (
            previous is None and
            goal_scope_requires_previous(state)
        )
        errors = validate(state)
        if previous_required:
            errors.append('previous state required for goal scope validation')
        transition_errors = []
        if previous is not None:
            transition_errors = validate_transition(previous, state)
        routed = route(state) if args.mode in ('next', 'final') else None
        if not errors and routed is not None and routed.get('action') == 'present_plan':
            plan = state['plan']
            old_plan = previous.get('plan') if isinstance(previous, dict) else None
            if (not isinstance(old_plan, dict) or not isinstance(old_plan.get('presented'), bool) or
                    (plan.get('presented') is True and
                     (old_plan.get('presented') is not True or old_plan.get('evidence') != plan.get('evidence')))):
                transition_errors.append('formal plan display requires the preceding discussion or presentation state')
        errors.extend(transition_errors)
        if args.mode == 'final':
            discussion_readback = []
            if not errors:
                recorded_graph = None
                if state.get('phase') == 'discussion':
                    recorded_graph = check_final_record(payload.get('discussion_record'), state.get('branch_history', []),
                                                        readback=discussion_readback,
                                                        decision_ids=[item['id'] for item in state.get('decisions', [])])
                errors.extend(validate_discussion_final(state, draft_reply, discussion_handoff, recorded_graph))
            errors.extend(validate_plan_final(state, draft_reply, payload, routed))
            result = {'ok': not errors, 'errors': errors}
            if not errors and 'readback_ranges' in (payload.get('discussion_record') or {}):
                result['discussion_readback'] = discussion_readback
        elif args.mode == 'next':
            result = routed
            if previous_required:
                result = {'action': 'repair_state', 'errors': errors}
        else:
            result = {'ok': not errors, 'errors': errors}
        if transition_errors and isinstance(state, dict):
            is_paused = result.get('action') == 'paused' or (result.get('action') == 'wait_interruption' and result.get('status') == 'paused')
            if args.mode == 'next' and is_paused:
                result['errors'] = errors
            else:
                result = {'action': 'repair_state', 'errors': errors} if args.mode == 'next' else {'ok': False, 'errors': errors}
        if (result.get('action') == 'complete' and
                isinstance(state, dict) and
                state.get('completion_basis') == 'user_requested'):
            result['instruction'] = USER_REQUESTED_COMPLETION_GUIDANCE
        elif result.get('action') in GUIDANCE:
            result['instruction'] = GUIDANCE[result['action']]
        if args.mode == 'final':
            result['scope'] = 'structure_and_changes_and_reply' if previous is not None else 'structure_and_reply'
        else:
            result['scope'] = 'structure_and_changes' if previous is not None else 'structure_only'
        add_error_diagnostics(result, state, previous)
        if args.emit_state and not errors and not result.get('original_state_errors'):
            result['state'] = state
        print(json.dumps(result, ensure_ascii=False))
        safe_actions = ('paused', 'handle_interruption', 'wait_interruption', 'reconcile_interruption')
        return bool(errors) and result.get('action') not in safe_actions
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        print(json.dumps({'ok': False, 'errors': [str(exc)]}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
