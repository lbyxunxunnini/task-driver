# Packet Templates

这些是最小合法 packet 模板。字段名和枚举值是机器契约，必须保持英文；用户可见解释可按 `references/glossary.md` 显示中文名。

## SpecPacket

```yaml
spec_packet:
  spec_path: docs/task-driver/specs/YYYY-MM-DD--slug.md | inline
  goal: "[一句话目标]"
  target:
    target_id: "[slug]"
    target_statement: "[外部可观察目标]"
    success_definition: "[完成状态，必须映射到 AC 和最终验证]"
    quality_level: mvp | polished | production
    stop_or_loop_conditions: "[失败、partial、plan-revision、brainstorming 回路条件]"
  decision_trace:
    - layer: 整体目标 | 大类/规划轴 | 范围切片 | 小项目/模块 | 行为细节 | 实现约束
      decision_point: "[决策问题]"
      options_summary: "[2-3 个选项摘要]"
      decision: "[用户选择或 ASM-N]"
      impact: "[对 Scope / AC / Risks / Verification 的影响]"
  grilling_summary:
    shared_understanding: true
    unresolved_branches: []
    key_tradeoffs: []
    rejected_paths: []
  design_tree_coverage:
    - branch_id: B1
      name: "[分支名]"
      parent: root
      layer: 整体目标
      status: decided | deferred | out_of_scope
      decision_ref: "[Decision Trace 行或 ASM-N]"
      blocks: []
  acceptance_criteria:
    - id: AC-1
      description: "[可观察验收项]"
      verification: "[命令、文件检查、截图、日志或人工证据]"
  constraints:
    - "[精确约束]"
  quality_level: mvp | polished | production
  approved_by_user: true
  status: approved
```

## PlanPacket

```yaml
plan_packet:
  plan_path: docs/task-driver/plans/YYYY-MM-DD--slug.md | inline
  ledger_path: docs/task-driver/ledgers/YYYY-MM-DD--slug.md | inline
  plan_version: v1
  predecessor: 无
  gate_mode: strict | standard | lite
  execution_mode: single-agent | multi-agent-review | multi-agent-parallel | degraded-single-skill
  tasks:
    - id: T-001
      owner_role: Implementer
      objective: "[必须追溯到 target_id、Decision Trace、AC 或 Constraints]"
      files:
        - path/to/file
      verification:
        - "[命令或确定性检查]"
      acceptance_ac_ids:
        - AC-1
  stop_conditions:
    - "[需要停机回问、blocked、plan-revision 或 brainstorming 的条件]"
  status: approved
```

## TaskResult

```yaml
task_result:
  task_id: T-001
  status: done | blocked | partial
  files_changed:
    - path/to/file
  commands_run:
    - command: "[实际运行命令]"
      exit_code: 0
  evidence:
    - id: EV-1
      command: "[命令或检查]"
      result: "[结果摘要]"
      strength: strong | medium | weak | stale
      covers_requirement_ids:
        - AC-1
  ac_coverage:
    - ac_id: AC-1
      covered: full | partial | none
      evidence:
        - EV-1
  deviations_from_plan: []
```

## ReviewReport

```yaml
review_report:
  task_id: T-001
  status: pass | needs_fix | blocked
  findings:
    - severity: critical | important | minor
      file: path/to/file
      issue: "[问题]"
      required_fix: "[必需修复]"
```

## VerificationReport

```yaml
verification_report:
  status: met | partial | not_met | blocked | awaiting_user_acceptance | accepted_by_user | rejected_by_user
  gate_mode: strict | standard | lite
  execution_mode: single-agent | multi-agent-review | multi-agent-parallel | degraded-single-skill
  coverage:
    - ac_id: AC-1
      evidence_ref: EV-1
      evidence_strength: strong | medium | weak | stale
      status: met | partial | not_met | blocked
  pre_acceptance_self_check:
    plan_tasks: pass | partial | fail
    review_reports: pass | partial | fail
    ac_coverage: pass | partial | fail
    verification_strategy: pass | partial | fail
    scope_drift: pass | fail
    quality_gate: pass | N/A | fail
    residual_risk: pass | partial | fail
  unmet_requirements: []
  delivery_acknowledged_by_user: pending
  quality_score:
    overall: 1.0-5.0 | N/A
    dimensions: {}
    threshold: 3 | 4 | 4.5
    decision: pass | improve | blocked | N/A
    evidence_refs:
      - EV-1
    rationale: "[评分理由或 N/A 原因]"
```
