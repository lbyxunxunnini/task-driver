# Packet Templates

这些是最小合法 packet 模板。字段名和枚举值是机器契约，必须保持英文；用户可见解释可按 `references/glossary.json` 显示中文名。

## 面向用户展示规则

当 agent 向用户展示 packet 内容时，必须将英文字段名转换为 `中文[英文]` 格式。转换规则：

1. **字段名转换**：`spec_path` → `需求规格路径[spec_path]`、`approved_by_user` → `用户已确认[approved_by_user]`
2. **枚举值转换**：`status: approved` → `状态[status]: 已确认[approved]`、`quality_level: polished` → `质量层级[quality_level]: 精打磨[polished]`
3. **布尔值保持**：`true`/`false` 保持原值，但字段名需转换
4. **数组/对象**：内部字段同样需要转换

**示例转换**：

机器契约（写入 ledger/spec 时）：
```yaml
spec_packet:
  spec_path: .task-driver/specs/20260707-1200-migrate.md
  goal: "解决鸿蒙端播放问题"
  quality_level: polished
  approved_by_user: true
  status: approved
```

面向用户展示：
```markdown
**需求规格交接包[SpecPacket]**

| 字段 | 值 |
|---|---|
| 需求规格路径[spec_path] | .task-driver/specs/20260707-1200-migrate.md |
| 目标[goal] | 解决鸿蒙端播放问题 |
| 质量层级[quality_level] | 精打磨[polished] |
| 用户已确认[approved_by_user] | true |
| 状态[status] | 已确认[approved] |
```

**PlanPacket 展示示例**：

机器契约：
```yaml
plan_packet:
  plan_path: .task-driver/plans/20260707-1200-migrate.md
  ledger_path: .task-driver/ledgers/20260707-1200-migrate.md
  gate_mode: standard
  execution_mode: single-agent
  quality_level: polished
  status: draft
  plan_version: v1
  tasks:
    - id: T-001
      name: 修改 audio_preview_mixin.dart
      files: [lib/common/mixins/audio_preview_mixin.dart]
      acceptance: [AC-1, AC-2, AC-3, AC-4]
```

面向用户展示：
```markdown
**计划交接包[PlanPacket]**

**基本信息**
| 字段 | 值 |
|---|---|
| 计划路径[plan_path] | .task-driver/plans/20260707-1200-migrate.md |
| 执行台账路径[ledger_path] | .task-driver/ledgers/20260707-1200-migrate.md |
| 目标ID[target_id] | fix-ohos-audio-preview-2026-07-07 |
| 目标[goal] | 用 just_audio 替代 audioplayers，解决鸿蒙端音色试听播放失败问题 |
| 门禁模式[gate_mode] | 标准模式[standard] |
| 执行模式[execution_mode] | 单智能体模式[single-agent] |
| 质量层级[quality_level] | 精打磨[polished] |
| 状态[status] | 草稿[draft] |
| 计划版本[plan_version] | v1 |

**任务列表[tasks]**
| 任务ID | 名称 | 文件 | 验收标准 |
|---|---|---|---|
| T-001 | 修改 audio_preview_mixin.dart | lib/common/mixins/audio_preview_mixin.dart | AC-1, AC-2, AC-3, AC-4 |
| T-002 | 修改 timbre_audio_preview_mixin.dart | lib/screens/timbre/utils/timbre_audio_preview_mixin.dart | AC-1, AC-2, AC-3, AC-4 |
| ... | ... | ... | ... |

**验证策略[verification_strategy]**
| 类型 | 命令 | 覆盖标准 | 证据强度 |
|---|---|---|---|
| 静态分析 | flutter analyze --no-fatal-infos --no-fatal-warnings | AC-5 | 强证据[strong] |
| 真机测试 | - | AC-1, AC-2, AC-3, AC-4 | 强证据[strong] |

**停机条件[stop_conditions]**
- 如果 just_audio_ohos 在鸿蒙端不可用
- 如果状态模型适配遗漏
- 如果静态分析有错误

**假设[assumptions]**
| ID | 内容 | 验证方式 |
|---|---|---|
| ASM-1 | just_audio_ohos 已集成且可用 | T-010 真机测试 |
| ASM-2 | 状态模型适配可行 | T-007, T-008 静态分析 |
```

## SpecPacket

```yaml
spec_packet:
  spec_path: .task-driver/specs/YYYYMMDD-HHmm-主题.md | inline
  goal: "[一句话目标]"
  target:
    target_id: "[slug]"
    target_statement: "[外部可观察目标]"
    success_definition: "[完成状态，必须映射到 AC 和最终验证]"
    scope_denominator:
      - "[目标单元，例如模块/文件族/命令/配置/测试/文档/用户路径/阶段]"
    target_principles:
      - "[冲突取舍原则，例如完整性优先于速度]"
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
  plan_path: .task-driver/plans/YYYYMMDD-HHmm-主题.md | inline
  ledger_path: .task-driver/ledgers/YYYYMMDD-HHmm-主题.md | inline
  plan_version: v1
  predecessor: 无
  gate_mode: strict | standard | lite
  execution_mode: single-agent | multi-agent-review | multi-agent-parallel | degraded-single-skill
  target_coverage_matrix:
    - target_unit: "[scope_denominator 中的目标单元]"
      task_ids: [T-001]
      verification_refs: [AC-1]
      status: planned
  decomposition_strategy:
    axis: 阶段 | 模块 | 风险 | 用户路径 | 产物类型 | 协议层级 | 问题类型
    levels: "[Phase -> Task -> Step -> Verification]"
    outputs: "[每层产物]"
    verification_by_level: "[每层验收方式]"
    granularity_floor: "文件 + 行为/内容变化 + AC 引用 + 功能级验证"
  tasks:
    - id: T-001
      owner_role: Implementer
      objective: "[必须追溯到 target_id、Decision Trace、AC 或 Constraints]"
      target_units:
        - "[目标单元]"
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
  target_coverage:
    - target_unit: "[目标单元]"
      task_ref: T-001
      evidence_ref: EV-1
      evidence_strength: strong | medium | weak | stale
      status: met | partial | not_met | blocked
  pre_acceptance_self_check:
    plan_tasks: pass | partial | fail
    review_reports: pass | partial | fail
    ac_coverage: pass | partial | fail
    target_coverage: pass | partial | fail
    verification_strategy: pass | partial | fail
    scope_drift: pass | fail
    quality_gate: pass | N/A | fail
    residual_risk: pass | partial | fail
    self_test_improve_loop: pass | partial | fail
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
