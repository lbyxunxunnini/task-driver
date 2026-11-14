#!/usr/bin/env python3
"""Validate a task-driver checkpoint.

The caller owns semantic interpretation and must supply evidence references.
This script cannot establish that a reference supports a claimed decision.
"""
import sys
sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import re

PHASES = {'analysis', 'discussion', 'planning', 'goals', 'execution', 'verification', 'review'}
STATUSES = {'continue', 'wait_user', 'wait_tool', 'blocked', 'paused', 'complete'}
GATES = ('plan', 'goals', 'execution', 'subagents')
INTERRUPTION_STATUSES = STATUSES | {'cancelled'}
GOAL_KINDS = {'changed', 'associated'}
COMPLETION_BASES = {'evidence', 'user_requested'}
GOAL_TRACKING_MODES = {'host', 'plan', 'conversation', 'unavailable'}
GOAL_TRACKING_FALLBACK_MODES = {'plan', 'conversation'}
STEP_STATUSES = {'pending', 'in_progress', 'done', 'blocked'}
GUIDANCE = {
    'present_incomplete_plan': '先读取或复用本 skill 的 references/planning.md、references/goals.md 及 references/templates.md 的目标草案章节，再在正文交付标明缺口的讨论稿，不能称为正式计划或请求执行。',
    'verify_plan_request': '核对当前计划请求与已交付草案的实际对应关系，再更新状态；不要重复提问或编造交付。',
    'present_plan': '先读取或复用本 skill 的 references/planning.md、references/goals.md 及 references/templates.md 的目标草案章节，按方法核对正文和状态，讨论闭合后在正文一起展示正式计划和目标；用户明确限制只展示其中一项时，说明严格流程并等待调整范围。展示不等于确认或执行授权，内容尚无有效确认时不提供执行选项；用户明确本轮不执行时，只确认尚缺的计划/目标内容，不问“是否按计划执行”，也不承诺“确认后就开始”。用户后续明确授权时沿用有效确认继续，不重复询问。',
    'request_plan_transition': '总结有效决定，完成 semantic_review 后最后询问是否结束讨论并开始展示正式计划与目标；措辞可自然变化。',
    'resolve_pending': '处理尚有影响的事项：能调查先调查，委托范围内自行决定，其余讨论。讨论阶段最终回复必须始终以一个问题结束，完成 semantic_review 后再收口，不得仅汇报分析；不要重问已决事项。',
    'check_coverage': '先核对目标、已有资料、决定和未决事项，再以新状态检查；不得编造问题。',
    'continue_local': '先完成已获授权的独立或局部动作，不扩大用户限定的范围；原等待或受阻状态保持不变。',
    'local_complete': '交付局部结果并保留原任务恢复点。',
    'check_operation': '仅在查询权限内只读核实原操作及回执；不授权新操作或重试，结果未知时不得重复执行副作用动作。',
    'handle_operation_failure': '原操作已失败且阻塞下一步；先按审查模块分类，保留失败证据，不重复执行，不把局部任务标记完成。',
    'scope_complete': '本轮只交付用户明确限定的内容；交付后停止，保留整体任务恢复点，不追加问题或推进下一阶段。',
    'complete': '完成前逐项核对 goals.included：每项都必须在 evidence_map 中有非空证据，excluded 不得计入完成；证据不足时保持未完成。',
    'repair_state': '修正状态结构；旧目标补录 included、excluded、evidence_map 和 goal_scope_baseline 后继续。若用户明确要求结束/完成但仍有未验证项，先设置 completion_basis:user_requested，记录用户来源、completion_report 和 unverified_goals，再重试；不要把用户结束要求当成验收或宣称已验证。',
    'handle_interruption': '先处理当前临时请求，核对用户与宿主授权；业务执行仍须满足原有执行门槛，不扩大原任务授权。',
    'reconcile_interruption': '核对临时结果、恢复点、最新用户要求和实际现场；正文先交付临时结果，再接回对应事项。用户明确暂停时保持暂停。',
    'begin_execution': '执行入口尚未通过。先核对分析闭合、讨论闭合、编号步骤、计划与目标确认、执行授权、子代理设置和目标跟踪回执；运行 begin 并取得 execution_receipt 后才能开始业务动作。',
    'start_step': '只开始当前编号步骤；取得实际结果和证据后再标记完成，不能提前勾选后续步骤。',
    'continue_step': '继续当前进行中的编号步骤；完成并核对证据后才进入下一步。',
    'step_blocked': '当前步骤受阻；先说明已完成部分、失败原因和是否影响后续步骤，不得跳过该步骤。',
    'steps_complete': '所有编号步骤已完成；只能进入验证与审查，不得继续做未列入计划的新业务动作。',
    'continue_analysis': '当前仍在分析阶段；只允许补事实、核范围和进入讨论，不得执行任何业务写入。',
}
USER_REQUESTED_COMPLETION_GUIDANCE = '用户明确要求完成：按要求将业务标记完成，但必须在 unverified_goals 和正文中逐项说明未验证目标、原因和影响，并记录 completion_request_source；不得写成所有目标已验证。'

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
        if not isinstance(references, list):
            errors.append('goals.evidence_map.' + ident + ' must be a list')
        elif not references or any(not isinstance(ref, str) or not ref.strip() for ref in references):
            errors.append('goals.evidence_map.' + ident + ' requires nonempty evidence references')

    if require_completion_evidence:
        for ident in sorted(included_ids):
            if not evidence_map.get(ident):
                errors.append('goal evidence missing: ' + ident)
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
        missing = [ident for ident in sorted(included_ids) if not evidence_map.get(ident)]
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
            for index, step in enumerate(steps):
                if (isinstance(step, dict) and isinstance(step.get('action'), str) and
                        step['action'] not in allowed_actions):
                    errors.append(
                        'plan.steps[' + str(index) + '] action is not in execution_scope.allowed_actions'
                    )
        if (not isinstance(scope.get('source'), str) or
                not scope['source'].strip()):
            errors.append('execution_scope.source required')

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
        if (not isinstance(current.get('plan_revision_source'), str) or
                not current['plan_revision_source'].strip()):
            errors.append('changed plan evidence requires plan_revision_source')
        elif current.get('plan_revision_source') == previous.get('plan_revision_source'):
            errors.append('changed plan evidence requires a new plan_revision_source')
    old_execution_begun = previous.get('execution_begun') is True
    new_execution_begun = current.get('execution_begun') is True
    if old_execution_begun and not new_execution_begun:
        if (not isinstance(current.get('execution_reset_source'), str) or
                not current['execution_reset_source'].strip()):
            errors.append('stopping begun execution requires execution_reset_source')
    old_scope = previous.get('execution_scope')
    new_scope = current.get('execution_scope')
    if old_scope != new_scope:
        if old_execution_begun and not new_execution_begun and not current.get('execution_reset_source'):
            errors.append('changed execution_scope requires execution_reset_source')
        if old_execution_begun and new_execution_begun:
            errors.append('changed execution_scope requires stopping and a new begin')
        if (isinstance(old_scope, dict) and isinstance(new_scope, dict) and
                old_scope.get('source') == new_scope.get('source')):
            errors.append('changed execution_scope requires a new source')
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
    if (status == 'blocked' and isinstance(independent, str) and independent.strip() and
            independent_action_allowed(s)):
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
                'next_action': '仅在本轮范围内只读核对既有证据；新业务动作另取有效入口'}
    if (s['phase'] == 'execution' and s.get('status') == 'continue' and
            not checking_operation and s.get('execution_begun') is not True):
        return {'action': 'begin_execution', 'next_action': '取得执行入口回执后继续'}
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
                return {'action': 'steps_complete', 'next_action': '进入验证与审查'}
    if s.get('local_only') and s.get('local_done'):
        if s.get('coverage_checked') is not True:
            return {'action': 'check_coverage'}
        return {'action': 'local_complete'}
    if s.get('local_only'):
        steps = s.get('plan', {}).get('steps', [])
        if (steps and all(isinstance(step, dict) and step.get('status') == 'done' for step in steps)):
            return {'action': 'steps_complete', 'next_action': '进入验证与审查'}
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
    if s['phase'] == 'analysis':
        return {'action': 'continue_analysis', 'next_action': '完成分析后进入讨论'}
    return {'action': 'continue_current_phase', 'next_action': s['next_action']}


def begin_execution(s, previous=None):
    """Return the one-time execution receipt only after the full entry gate passes."""
    if not isinstance(s, dict):
        return {'ok': False, 'errors': ['checkpoint must be an object']}
    errors = validate(s)
    if previous is None and goal_scope_requires_previous(s):
        errors.append('previous state required for execution begin')
    if previous is not None:
        errors.extend(validate_transition(previous, s))
    if s.get('phase') != 'execution':
        errors.append('begin requires phase execution')
    if s.get('status') != 'continue':
        errors.append('begin requires status continue')
    if s.get('execution_begun') is True:
        errors.append('execution already begun; reuse the existing receipt or start a new task')
    steps = s.get('plan', {}).get('steps', [])
    progressed = [step for step in steps if isinstance(step, dict) and
                  step.get('status') in ('done', 'in_progress')]
    if progressed:
        renewing = (
            isinstance(previous, dict) and previous.get('execution_begun') is True and
            previous.get('phase') in ('execution', 'verification', 'review') and
            previous.get('status') != 'complete' and not validate(previous) and
            previous.get('execution_receipt') == execution_receipt(previous) and
            isinstance(s.get('execution_reset_source'), str) and
            bool(s['execution_reset_source'].strip())
        )
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
            current_operations = {op['id']: op for op in s.get('operations', []) if isinstance(op, dict) and 'id' in op}
            for op in previous.get('operations', []):
                if op.get('blocks_next') is True and op.get('status') in ('running', 'unknown'):
                    observed = current_operations.get(op['id'], {})
                    if (observed.get('reference') != op['reference'] or
                            observed.get('status') not in ('succeeded', 'failed') or
                            not observed.get('evidence')):
                        errors.append('renewed begin must reconcile the original operation: ' + op['id'])
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


def validate_discussion_final(s, reply, handoff):
    """Validate a discussion question, user-scoped stop, or actual tool wait."""
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
        if (routed.get('independent_action') or routed.get('independent_checks') or
                pending_plan_request_action(s)):
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


def add_error_diagnostics(result, state):
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
                'hint': '按实际环节填写合法值；不自动转换或推进阶段。',
            }
        elif error in ('presented plan requires evidence', 'presented goals require evidence'):
            field = 'plan' if error == 'presented plan requires evidence' else 'goals'
            detail = {
                'field': field + '.evidence',
                'hint': '准备展示不等于已经展示。只有实际已交付时才填写可核实消息来源；'
                        '尚未展示时保留真实状态，按 next 返回动作展示，不能填未来回复来通过检查。'
                        '已有展示不能为绕过检查改成未展示，应恢复其真实来源。',
            }
        if detail is not None:
            if source == 'original_state_errors':
                detail['error_source'] = source
            diagnostics.append(detail)
    if diagnostics:
        result['diagnostics'] = diagnostics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('check', 'next', 'begin', 'final'))
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
            previous = payload.get('previous') if isinstance(payload, dict) else None
            state = payload.get('state') if isinstance(payload, dict) and 'state' in payload else payload
            draft_reply = None
            discussion_handoff = None
        if args.mode == 'begin':
            result = begin_execution(state, previous)
            add_error_diagnostics(result, state)
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
            errors.extend(transition_errors)
        if args.mode == 'final':
            errors.extend(validate_discussion_final(state, draft_reply, discussion_handoff))
            result = {'ok': not errors, 'errors': errors}
        elif args.mode == 'next':
            result = route(state)
            if previous_required:
                result = {'action': 'repair_state', 'errors': errors}
        else:
            result = {'ok': not errors, 'errors': errors}
        if previous is not None and transition_errors and isinstance(state, dict):
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
        add_error_diagnostics(result, state)
        print(json.dumps(result, ensure_ascii=False))
        safe_actions = ('paused', 'handle_interruption', 'wait_interruption', 'reconcile_interruption')
        return bool(errors) and result.get('action') not in safe_actions
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({'ok': False, 'errors': [str(exc)]}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
