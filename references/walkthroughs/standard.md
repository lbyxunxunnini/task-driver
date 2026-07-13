# Standard Walkthrough

场景：用户要求修复一个跨 3 个文件的 CLI bug，不涉及数据、权限、安全、发布或公共 API。

## Trigger

```text
tdr- 修复 CLI --json 输出空数组时格式错误的问题，从复现到验证完整跑完
```

## Decision

- gate_mode: standard
- execution_mode: single-agent
- 原因：跨 2-5 文件、默认风险、需要完整 spec / plan / ledger。

## Spec Summary

```yaml
spec_packet:
  spec_path: .task-driver/specs/20260707-1200-cli-json-empty-array.md
  goal: "修复 CLI --json 空数组输出格式"
  target:
    target_id: cli-json-empty-array
    target_statement: "CLI 在空结果下输出合法 JSON 数组。"
    success_definition: "AC-1 到 AC-4 均有 strong fresh evidence。"
    scope_denominator: ["空结果 JSON 输出", "JSON.parse 可解析性", "非空 JSON 回归", "默认文本输出回归"]
    target_principles: ["最小行为修复优先", "不改变错误输出和 formatter 架构"]
    quality_level: polished
    stop_or_loop_conditions: "复现不成立回到 brainstorming；测试路径错误回到 planning；实现缺陷回到 executing。"
  decision_trace:
    - layer: 整体目标
      decision_point: "空结果应该输出什么?"
      options_summary: "[] / null / 空字符串"
      decision: "[]"
      impact: "AC 聚焦合法 JSON 数组。"
    - layer: 行为细节
      decision_point: "错误输出是否改变?"
      options_summary: "保持 / 一并规范化"
      decision: "保持"
      impact: "Non-Goals 排除错误输出重构。"
  grilling_summary:
    shared_understanding: true
    unresolved_branches: []
    key_tradeoffs: ["最小行为修复，不改错误输出"]
    rejected_paths: ["重写 JSON formatter"]
  design_tree_coverage:
    - branch_id: B1
      name: empty result behavior
      parent: root
      layer: 行为细节
      status: decided
      decision_ref: "Decision Trace: 整体目标"
      blocks: []
  acceptance_criteria:
    - id: AC-1
      description: "--json 空结果输出 []"
      verification: "cli search none --json"
    - id: AC-2
      description: "输出可被 JSON.parse 解析"
      verification: "node -e 'JSON.parse(...)'"
    - id: AC-3
      description: "非空结果 JSON 行为不回归"
      verification: "existing json fixture test"
    - id: AC-4
      description: "默认文本输出不变"
      verification: "snapshot or direct CLI check"
  constraints: ["不重写 formatter 架构", "不改变错误输出"]
  quality_level: polished
  approved_by_user: true
  status: approved
```

## GoalDraft Summary

```yaml
goal_draft:
  target_id: cli-json-empty-array
  goal_provider: ledger-only
  outcome: "CLI 在空结果下输出合法 JSON 数组。"
  completion_condition: "AC-1 到 AC-4 均有 strong fresh evidence。"
  verification_surface:
    - "cli search none --json"
    - "node -e 'JSON.parse(...)'"
    - "existing json fixture test"
    - "snapshot or direct CLI check"
  constraints: ["最小行为修复优先", "不改变错误输出和 formatter 架构"]
  boundaries: ["空结果 JSON 输出", "JSON.parse 可解析性", "非空 JSON 回归", "默认文本输出回归"]
  iteration_policy: "每轮记录改动、证据、未满足项和下一步假设；同一问题最多两轮后路由。"
  blocked_stop_condition: "复现不成立回到 brainstorming；测试路径错误回到 planning；实现缺陷回到 executing。"
  goal_detection:
    required: true
    verifier: isolated_goal_verifier
    context_policy: "只提供 packet、ledger evidence、VerificationReport draft 和必要命令输出。"
    fallback_policy: "允许 new-session verifier / external verifier / manual isolated review；禁止 same-context self-check。"
    evidence_required: ["coverage[]", "target_coverage[]", "pre_acceptance_self_check"]
  activation_command: "N/A"
  source_packet_ref: .task-driver/specs/20260707-1200-cli-json-empty-array.md
  status: active
```

## Plan Summary

```yaml
plan_packet:
  plan_path: .task-driver/plans/20260707-1200-cli-json-empty-array.md
  ledger_path: .task-driver/ledgers/20260707-1200-cli-json-empty-array.md
  plan_version: v1
  predecessor: 无
  gate_mode: standard
  execution_mode: single-agent
  target_coverage_matrix:
    - target_unit: "空结果 JSON 输出"
      task_ids: [T-001, T-002]
      verification_refs: [AC-1]
      status: planned
    - target_unit: "JSON.parse 可解析性"
      task_ids: [T-001, T-002]
      verification_refs: [AC-2]
      status: planned
    - target_unit: "非空 JSON 回归"
      task_ids: [T-002]
      verification_refs: [AC-3]
      status: planned
    - target_unit: "默认文本输出回归"
      task_ids: [T-002]
      verification_refs: [AC-4]
      status: planned
  decomposition_strategy:
    axis: 用户路径
    levels: "Task -> Step -> Verification"
    outputs: "失败测试、formatter 修复、回归验证"
    verification_by_level: "CLI JSON 测试、formatter 回归测试"
    granularity_floor: "文件 + 行为变化 + AC 引用 + 功能级测试"
  tasks:
    - id: T-001
      owner_role: Implementer
      objective: "新增空数组 JSON 失败测试"
      target_units: ["空结果 JSON 输出", "JSON.parse 可解析性"]
      files: [tests/cli-json.test.ts]
      verification: ["npm test -- cli-json"]
      acceptance_ac_ids: [AC-1, AC-2]
    - id: T-002
      owner_role: Implementer
      objective: "修复 formatter 空结果分支"
      target_units: ["空结果 JSON 输出", "JSON.parse 可解析性", "非空 JSON 回归", "默认文本输出回归"]
      files: [src/cli.ts, src/formatters/json.ts]
      verification: ["npm test -- cli-json", "npm test -- formatter"]
      acceptance_ac_ids: [AC-1, AC-2, AC-3, AC-4]
  stop_conditions:
    - "需要改变公共 JSON schema"
    - "测试显示默认文本输出变化"
  status: approved
```

## Execution And Review

```yaml
task_result:
  task_id: T-002
  status: done
  files_changed: [src/cli.ts, src/formatters/json.ts, tests/cli-json.test.ts]
  commands_run:
    - command: "npm test -- cli-json"
      exit_code: 0
    - command: "npm test -- formatter"
      exit_code: 0
  evidence:
    - id: EV-1
      command: "npm test -- cli-json"
      result: "12 passed"
      strength: strong
      covers_requirement_ids: [AC-1, AC-2, AC-3]
    - id: EV-2
      command: "npm test -- formatter"
      result: "18 passed"
      strength: strong
      covers_requirement_ids: [AC-4]
  ac_coverage:
    - ac_id: AC-1
      covered: full
      evidence: [EV-1]
    - ac_id: AC-2
      covered: full
      evidence: [EV-1]
    - ac_id: AC-3
      covered: full
      evidence: [EV-1]
    - ac_id: AC-4
      covered: full
      evidence: [EV-2]
  deviations_from_plan: []

review_report:
  task_id: T-002
  status: pass
  findings: []
```

## Verification

```yaml
verification_report:
  status: awaiting_user_acceptance
  gate_mode: standard
  execution_mode: single-agent
  coverage:
    - ac_id: AC-1
      evidence_ref: EV-1
      evidence_strength: strong
      status: met
    - ac_id: AC-2
      evidence_ref: EV-1
      evidence_strength: strong
      status: met
    - ac_id: AC-3
      evidence_ref: EV-1
      evidence_strength: strong
      status: met
    - ac_id: AC-4
      evidence_ref: EV-2
      evidence_strength: strong
      status: met
  target_coverage:
    - target_unit: "空结果 JSON 输出"
      task_ref: T-002
      evidence_ref: EV-1
      evidence_strength: strong
      status: met
    - target_unit: "JSON.parse 可解析性"
      task_ref: T-002
      evidence_ref: EV-1
      evidence_strength: strong
      status: met
    - target_unit: "非空 JSON 回归"
      task_ref: T-002
      evidence_ref: EV-1
      evidence_strength: strong
      status: met
    - target_unit: "默认文本输出回归"
      task_ref: T-002
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
    quality_gate: pass
    residual_risk: pass
    self_test_improve_loop: pass
  isolated_goal_detection:
    verifier: isolated_goal_verifier
    context_inputs: ["SpecPacket", "GoalDraft", "PlanPacket", "ledger evidence", "VerificationReport draft"]
    evidence_refs: [EV-1, EV-2, EV-3]
    status: pass
    finding: "All JSON output goal boundaries are proven by fresh verification evidence."
  unmet_requirements: []
  delivery_acknowledged_by_user: pending
  quality_score:
    overall: 4.3
    threshold: 4
    decision: pass
    evidence_refs: [EV-1, EV-2]
    rationale: "polished 门槛下，核心行为、回归和默认输出均有 strong evidence。"
```
