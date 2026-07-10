# Packet Templates

这些是最小合法 packet 模板。字段名和枚举值是机器契约，必须保持英文；用户可见解释可按 `references/glossary.json` 显示中文名。

## 分组表格展示规则

当 agent 向用户展示 packet 内容时，**必须使用分组表格格式**，避免 YAML 嵌套。每个 packet 按逻辑分为多个组，每组使用独立表格。

**分组原则**：
1. 简单分组用两列（字段名 | 值）
2. 复杂分组用多列（根据字段特点设计）
3. 每组独立成表，用户可快速定位

**SpecPacket 分组表格展示模板**：

```markdown
**需求规格交接包[SpecPacket]**

**基本信息**
| 字段 | 值 |
|---|---|
| 需求规格路径[spec_path] | .task-driver/specs/YYYYMMDD-HHmm-主题.md |
| 目标[goal] | [一句话目标] |
| 质量层级[quality_level] | [mvp / 精打磨[polished] / 生产级[production]] |
| 用户已确认[approved_by_user] | [true / false] |
| 状态[status] | [草稿[draft] / 已确认[approved] / 已被替代[superseded]] |

**目标定义**
| 字段 | 值 |
|---|---|
| 目标ID[target_id] | [slug] |
| 目标陈述[target_statement] | [外部可观察目标] |
| 成功定义[success_definition] | [完成状态] |
| 范围分母[scope_denominator] | [目标单元列表] |
| 目标原则[target_principles] | [冲突取舍原则] |
| 停机条件[stop_or_loop_conditions] | [回路条件] |

**决策轨迹[decision_trace]**
| 层级[layer] | 决策点[decision_point] | 选项摘要[options_summary] | 决策[decision] | 影响[impact] |
|---|---|---|---|---|
| [整体目标 / 大类/规划轴 / 范围切片 / 小项目/模块 / 行为细节 / 实现约束] | [决策问题] | [2-3 个选项摘要] | [用户选择或 ASM-N] | [对 Scope / AC / Risks / Verification 的影响] |

**拷问摘要[grilling_summary]**
| 字段 | 值 |
|---|---|
| 共享理解[shared_understanding] | [true / false] |
| 未闭合分支[unresolved_branches] | [无 / 列出剩余分支] |
| 关键取舍[key_tradeoffs] | [关键取舍] |
| 拒绝方向[rejected_paths] | [明确拒绝的方向] |

**设计树覆盖[design_tree_coverage]**
| 分支ID[branch_id] | 分支[name] | 上游依赖[parent] | 层级[layer] | 状态[status] | 决策引用[decision_ref] | 阻塞项[blocks] |
|---|---|---|---|---|---|---|
| [B1] | [分支名] | [root / B-N] | [整体目标 / 大类/规划轴 / 范围切片 / 小项目/模块 / 行为细节 / 实现约束] | [已决定[decided] / 已延迟[deferred] / 超出范围[out_of_scope] / 待定[open]] | [Decision Trace 行或 ASM-N] | [B-N 或无] |

**验收标准[acceptance_criteria]**
| ID | 验收项[description] | 验证方式[verification] |
|---|---|---|
| [AC-1] | [可观察验收项] | [命令、文件检查、截图、日志或人工证据] |

**约束[constraints]**
- [精确约束]

**风险[risks]**
- [风险和缓解]
```

## 面向用户展示规则

当 agent 向用户展示 packet 内容时，**必须使用分组表格格式**，避免 YAML 嵌套。每个 packet 按逻辑分为多个组，每组使用独立表格。

**分组原则**：
1. 简单分组用两列（字段名 | 值）
2. 复杂分组用多列（根据字段特点设计）
3. 每组独立成表，用户可快速定位

**PlanPacket 分组表格展示模板**：

**面向用户展示（精简版）**：

```markdown
**计划交接包[PlanPacket]**

**基本信息**
| 字段 | 值 |
|---|---|
| 目标[goal] | [一句话目标] |
| 门禁模式[gate_mode] | [严格模式[strict]] |
| 执行模式[execution_mode] | [单智能体模式[single-agent] / 多智能体评审模式[multi-agent-review] / 多智能体并行模式[multi-agent-parallel] / 降级单技能模式[degraded-single-skill]] |
| 质量层级[quality_level] | [MVP / 精打磨[polished] / 生产级[production]] |
| 计划版本[plan_version] | [v1 / v2 / ...] |

**任务列表（共 N 项）**
- T-001 [任务名称] [AC-1]
- T-002 [任务名称] [AC-2]
- ...

**停机条件[stop_conditions]**
- [需要停机回问、blocked、plan-revision 或 brainstorming 的条件]
```

**内部交接完整版（面向用户时隐藏）**：

```markdown
**计划交接包[PlanPacket]**

**基本信息**
| 字段 | 值 |
|---|---|
| 计划路径[plan_path] | .task-driver/plans/YYYYMMDD-HHmm-主题.md |
| 执行台账路径[ledger_path] | .task-driver/ledgers/YYYYMMDD-HHmm-主题.md |
| 目标ID[target_id] | [slug] |
| 目标[goal] | [一句话目标] |
| 门禁模式[gate_mode] | [严格模式[strict]] |
| 执行模式[execution_mode] | [单智能体模式[single-agent] / 多智能体评审模式[multi-agent-review] / 多智能体并行模式[multi-agent-parallel] / 降级单技能模式[degraded-single-skill]] |
| 质量层级[quality_level] | [MVP / 精打磨[polished] / 生产级[production]] |
| 状态[status] | [草稿[draft] / 已确认[approved] / 已被替代[superseded]] |
| 计划版本[plan_version] | [v1 / v2 / ...] |

**目标覆盖矩阵[target_coverage_matrix]**
| 目标单元[target_unit] | 计划任务[task_ids] | 验证项[verification_refs] | 状态[status] |
|---|---|---|---|
| [scope_denominator 中的目标单元] | [T-001] | [AC-1] | [已计划[planned] / 进行中[in_progress] / 已完成[done]] |

**拆解策略[decomposition_strategy]**
| 字段 | 值 |
|---|---|
| 拆解轴[axis] | [阶段 / 模块 / 风险 / 用户路径 / 产物类型 / 协议层级 / 问题类型] |
| 拆解层级[levels] | [Phase -> Task -> Step -> Verification] |
| 产物[outputs] | [每层产物] |
| 验证方式[verification_by_level] | [每层验收方式] |
| 粒度下限[granularity_floor] | [文件 + 行为/内容变化 + AC 引用 + 功能级验证] |

**任务列表[tasks]**
| 任务ID[id] | 负责角色[owner_role] | 目标[objective] | 目标单元[target_units] | 文件[files] | 验证[verification] | 验收标准[acceptance_ac_ids] |
|---|---|---|---|---|---|---|
| [T-001] | [Implementer] | [必须追溯到 target_id、Decision Trace、AC 或 Constraints] | [目标单元] | [path/to/file] | [命令或确定性检查] | [AC-1] |

**停机条件[stop_conditions]**
- [需要停机回问、blocked、plan-revision 或 brainstorming 的条件]

**假设[assumptions]**
| ID | 内容 | 依据 | 验证点 | 失效处理 | 影响范围 |
|---|---|---|---|---|---|
| [ASM-1] | [具体假设] | [来自哪些文件、命令、日志或文档] | [在哪个任务或命令中验证] | [假设不成立时进入 blocked / plan-revision / brainstorming 的哪一路] | [影响哪些 T-NNN / AC-N] |
```

**TaskResult 分组表格展示模板**：

```markdown
**任务结果[TaskResult]**

**基本信息**
| 字段 | 值 |
|---|---|
| 任务ID[task_id] | [T-001] |
| 状态[status] | [已完成[done] / 受阻[blocked] / 部分完成[partial]] |

**改动文件[files_changed]**
- [path/to/file1]
- [path/to/file2]

**执行命令[commands_run]**
| 命令[command] | 退出码[exit_code] |
|---|---|
| [实际运行命令] | [0 / 非0] |

**证据[evidence]**
| ID | 命令[command] | 结果[result] | 证据强度[strength] | 覆盖标准[covers_requirement_ids] |
|---|---|---|---|---|
| [EV-1] | [命令或检查] | [结果摘要] | [强证据[strong] / 中等证据[medium] / 弱证据[weak] / 过期证据[stale]] | [AC-1] |

**AC 覆盖[ac_coverage]**
| AC ID | 覆盖状态[covered] | 证据[evidence] |
|---|---|---|
| [AC-1] | [完全覆盖[full] / 部分覆盖[partial] / 未覆盖[none]] | [EV-1] |

**偏离计划[deviations_from_plan]**
- [偏离内容]
```

**ReviewReport 分组表格展示模板**：

```markdown
**评审报告[ReviewReport]**

**基本信息**
| 字段 | 值 |
|---|---|
| 任务ID[task_id] | [T-001] |
| 状态[status] | [通过[pass] / 需要修复[needs_fix] / 受阻[blocked]] |

**评审发现[findings]**
| 严重程度[severity] | 文件[file] | 问题[issue] | 必需修复[required_fix] |
|---|---|---|---|
| [严重[Critical] / 重要[Important] / 次要[Minor]] | [path/to/file] | [问题描述] | [必需修复描述] |
```

**VerificationReport 分组表格展示模板**：

```markdown
**验证报告[VerificationReport]**

**基本信息**
| 字段 | 值 |
|---|---|
| 状态[status] | [已满足[met] / 部分完成[partial] / 未满足[not_met] / 受阻[blocked] / 等待用户验收[awaiting_user_acceptance] / 用户已接受[accepted_by_user] / 用户已拒绝[rejected_by_user]] |
| 门禁模式[gate_mode] | [严格模式[strict] / 标准模式[standard] / 轻量模式[lite]] |
| 执行模式[execution_mode] | [单智能体模式[single-agent] / 多智能体评审模式[multi-agent-review] / 多智能体并行模式[multi-agent-parallel] / 降级单技能模式[degraded-single-skill]] |

**AC 覆盖[coverage]**
| AC ID | 证据引用[evidence_ref] | 证据强度[evidence_strength] | 状态[status] |
|---|---|---|---|
| [AC-1] | [EV-1] | [强证据[strong] / 中等证据[medium] / 弱证据[weak] / 过期证据[stale]] | [已满足[met] / 部分完成[partial] / 未满足[not_met] / 受阻[blocked]] |

**目标覆盖[target_coverage]**
| 目标单元[target_unit] | 任务引用[task_ref] | 证据引用[evidence_ref] | 证据强度[evidence_strength] | 状态[status] |
|---|---|---|---|---|
| [目标单元] | [T-001] | [EV-1] | [强证据[strong] / 中等证据[medium] / 弱证据[weak] / 过期证据[stale]] | [已满足[met] / 部分完成[partial] / 未满足[not_met] / 受阻[blocked]] |

**验收前自检[pre_acceptance_self_check]**
| 检查项 | 状态 |
|---|---|
| 计划任务[plan_tasks] | [通过[pass] / 部分通过[partial] / 失败[fail]] |
| 评审报告[review_reports] | [通过[pass] / 部分通过[partial] / 失败[fail]] |
| AC 覆盖[ac_coverage] | [通过[pass] / 部分通过[partial] / 失败[fail]] |
| 目标覆盖[target_coverage] | [通过[pass] / 部分通过[partial] / 失败[fail]] |
| 验证策略[verification_strategy] | [通过[pass] / 部分通过[partial] / 失败[fail]] |
| 范围漂移[scope_drift] | [通过[pass] / 失败[fail]] |
| 质量门[quality_gate] | [通过[pass] / 不适用[N/A] / 失败[fail]] |
| 残余风险[residual_risk] | [通过[pass] / 部分通过[partial] / 失败[fail]] |
| 自检优化循环[self_test_improve_loop] | [通过[pass] / 部分通过[partial] / 失败[fail]] |

**未满足需求[unmet_requirements]**
| AC ID | 原因[reason] | 下一步动作[next_action] |
|---|---|---|
| [AC-1] | [原因] | [下一步动作] |

**用户验收状态[delivery_acknowledged_by_user]**
| 字段 | 值 |
|---|---|
| 状态 | [等待中[pending] / 已接受[true] / 已拒绝[false] / 部分接受[partial]] |

**质量评分[quality_score]**
| 字段 | 值 |
|---|---|
| 综合评分[overall] | [1.0-5.0 / 不适用[N/A]] |
| 维度[dimensions] | [维度详情] |
| 阈值[threshold] | [3 / 4 / 4.5] |
| 决定[decision] | [通过[pass] / 改进[improve] / 受阻[blocked] / 不适用[N/A]] |
| 证据引用[evidence_refs] | [EV-1] |
| 理由[rationale] | [评分理由或 N/A 原因] |
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
  gate_mode: strict
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
  gate_mode: strict
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
