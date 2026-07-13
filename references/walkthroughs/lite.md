# Lite Walkthrough

场景：用户要求修正文档中的一个错别字，只改一个非关键 Markdown 文件，有确定性检查方式。

## Trigger

```text
tdr- 修正 README 里 “verfication” 的拼写错误，并确认没有其他改动
```

## Decision

- gate_mode: lite
- execution_mode: single-agent
- 原因：单文件、低风险、不涉及代码行为、安全、发布、迁移或公共 API。

## Minimal Packets

```yaml
spec_packet:
  spec_path: inline
  goal: "修正 README 拼写错误"
  target:
    target_id: readme-typo-verification
    target_statement: "README 中 verification 拼写正确，且无额外文件改动。"
    success_definition: "AC-1 和 AC-2 有 fresh evidence。"
    scope_denominator: ["README.md 中的 verfication 错拼", "改动文件集合"]
    target_principles: ["最小改动优先", "不做文案重写"]
    quality_level: mvp
    stop_or_loop_conditions: "发现多处相关错拼可继续；发现范围扩大则停机回问。"
  decision_trace:
    - layer: 整体目标
      decision_point: "是否只修 spelling?"
      options_summary: "仅修 typo / 顺带润色段落"
      decision: "仅修 typo"
      impact: "Scope 限定为 README 单词替换。"
  grilling_summary:
    shared_understanding: true
    unresolved_branches: []
    key_tradeoffs: ["最小改动优先"]
    rejected_paths: ["顺带重写 README"]
  design_tree_coverage:
    - branch_id: B1
      name: typo scope
      parent: root
      layer: 范围切片
      status: decided
      decision_ref: "Decision Trace: 整体目标"
      blocks: []
  acceptance_criteria:
    - id: AC-1
      description: "README 不再包含 verfication"
      verification: "rg -n 'verfication' README.md exits 1"
    - id: AC-2
      description: "只修改 README.md"
      verification: "git diff --name-only"
  constraints: ["不做文案重写"]
  quality_level: mvp
  approved_by_user: true
  status: approved

goal_draft:
  target_id: readme-typo-verification
  goal_provider: ledger-only
  outcome: "README 中 verification 拼写正确，且无额外文件改动。"
  completion_condition: "AC-1 和 AC-2 有 fresh evidence。"
  verification_surface:
    - "rg -n 'verfication' README.md exits 1"
    - "git diff --name-only"
  constraints: ["最小改动优先", "不做文案重写"]
  boundaries: ["README.md 中的 verfication 错拼", "改动文件集合"]
  iteration_policy: "每轮记录改动、证据、未满足项和下一步假设；同一问题最多两轮。"
  blocked_stop_condition: "发现多处相关错拼可继续；发现范围扩大则停机回问。"
  goal_detection:
    required: true
    verifier: isolated_goal_verifier
    context_policy: "只提供 packet、ledger evidence、VerificationReport draft 和必要命令输出。"
    fallback_policy: "允许 new-session verifier / external verifier / manual isolated review；禁止 same-context self-check。"
    evidence_required: ["coverage[]", "target_coverage[]", "pre_acceptance_self_check"]
  activation_command: "N/A"
  source_packet_ref: inline
  status: active

plan_packet:
  plan_path: inline
  ledger_path: inline
  plan_version: v1
  predecessor: 无
  gate_mode: lite
  execution_mode: single-agent
  target_coverage_matrix:
    - target_unit: "README.md 中的 verfication 错拼"
      task_ids: [T-001]
      verification_refs: [AC-1]
      status: planned
    - target_unit: "改动文件集合"
      task_ids: [T-001]
      verification_refs: [AC-2]
      status: planned
  decomposition_strategy:
    axis: 产物类型
    levels: "Task -> Verification"
    outputs: "README 单词替换"
    verification_by_level: "rg 检查错拼 + git diff 文件范围"
    granularity_floor: "文件 + 文本变化 + AC 引用 + 确定性检查"
  tasks:
    - id: T-001
      owner_role: Implementer
      objective: "替换 README.md 中的错拼"
      target_units: ["README.md 中的 verfication 错拼", "改动文件集合"]
      files: [README.md]
      verification: ["rg -n 'verfication' README.md", "git diff --name-only"]
      acceptance_ac_ids: [AC-1, AC-2]
  stop_conditions: ["发现多个文件需要修改"]
  status: approved
```

## Execution

```yaml
task_result:
  task_id: T-001
  status: done
  files_changed: [README.md]
  commands_run:
    - command: "rg -n 'verfication' README.md"
      exit_code: 1
    - command: "git diff --name-only"
      exit_code: 0
  evidence:
    - id: EV-1
      command: "rg -n 'verfication' README.md"
      result: "no matches"
      strength: strong
      covers_requirement_ids: [AC-1]
    - id: EV-2
      command: "git diff --name-only"
      result: "README.md"
      strength: strong
      covers_requirement_ids: [AC-2]
  ac_coverage:
    - ac_id: AC-1
      covered: full
      evidence: [EV-1]
    - ac_id: AC-2
      covered: full
      evidence: [EV-2]
  deviations_from_plan: []

review_report:
  task_id: T-001
  status: pass
  findings: []
```

## Verification

```yaml
verification_report:
  status: awaiting_user_acceptance
  gate_mode: lite
  execution_mode: single-agent
  coverage:
    - ac_id: AC-1
      evidence_ref: EV-1
      evidence_strength: strong
      status: met
    - ac_id: AC-2
      evidence_ref: EV-2
      evidence_strength: strong
      status: met
  target_coverage:
    - target_unit: "README.md 中的 verfication 错拼"
      task_ref: T-001
      evidence_ref: EV-1
      evidence_strength: strong
      status: met
    - target_unit: "改动文件集合"
      task_ref: T-001
      evidence_ref: EV-2
      evidence_strength: strong
      status: met
  pre_acceptance_self_check:
    plan_tasks: pass
    review_reports: pass
    ac_coverage: pass
    target_coverage: pass
    verification_strategy: pass
    scope_drift: pass
    quality_gate: N/A
    residual_risk: pass
    self_test_improve_loop: pass
  isolated_goal_detection:
    verifier: isolated_goal_verifier
    context_inputs: ["SpecPacket", "GoalDraft", "PlanPacket", "ledger evidence", "VerificationReport draft"]
    evidence_refs: [EV-1, EV-2]
    status: pass
    finding: "README typo target and file boundary are proven by current evidence."
  unmet_requirements: []
  delivery_acknowledged_by_user: pending
  quality_score:
    overall: N/A
    decision: N/A
    rationale: "mvp 且低风险单文件 typo 修复。"
```

要点：lite 可以内联 spec/plan，但不能放宽 evidence strength；`medium` 仍最多只能标 `partial`。
