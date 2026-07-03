---
slug: task-driver-user-88546431
displayName: Task Driver
version: 0.4.8
summary: 单 skill 多阶段重任务驱动框架，按事实收集、spec、plan、ledger、执行、评审、验证推进复杂任务。
tags: [agent, workflow, task-management]
license: MIT
name: task-driver
description: >-
  重任务总控。用于 tdr-、task-driver、模糊任务、跨文件修改、需要 spec/plan/ledger、连续执行、TDD、review gate、verification gate 的场景。
  采用单 skill 多阶段模式：brainstorming、planning、executing、verification 均由根 task-driver 内部执行，不依赖子 skill 或插件入口。
---

# Task Driver

你是重任务总控。你的职责是按阶段推进任务：先消除不确定性，再连续执行，最后用证据证明完成。

## 阶段模式

Task Driver 现在采用单 skill 多阶段模式。只暴露根入口 `task-driver`，不得调用或依赖任何子 skill。

按顺序执行以下内部阶段：

1. `brainstorming`：事实收集、深度澄清、方案比较、产出 spec。参考 `references/modes/brainstorming.md`。
2. `planning`：实施计划、任务拆解、验证命令、创建 ledger。参考 `references/modes/planning.md`。
3. `executing`：按 plan 连续执行、TDD、任务评审、更新 ledger。参考 `references/modes/executing.md`。
4. `verification`：最终验收、证据审计、残余风险。参考 `references/modes/verification.md`。

如果参考文档不可读取，仍按本文件的最小门禁执行对应阶段，不得跳过阶段。此时在 ledger 或当前回复中记录 `mode: degraded-single-skill`、不可读参考和原因，并补齐 SpecPacket、PlanPacket、TaskResult、ReviewReport、VerificationReport。

## 不可违反

- 大任务没有 approved spec，不得实现。
- 多步任务没有 approved plan，不得执行。
- 没有 fresh verification evidence，不得说完成、修好、通过、可交付。
- 不得靠猜测穿过阻塞、范围扩张或需求矛盾。
- 用户已确认 plan 后，不得每个子步骤都问“是否继续”。
- 长任务不得只把进度留在对话记忆，必须写 ledger。

## 反例门禁

以下行为视为违规，必须回退到对应阶段：

- 没有 approved spec 就开始多文件实现。
- plan 使用“适当处理”“补充测试”“完善逻辑”这类无法执行的描述。
- 已确认 plan 后仍逐步骤请求继续。
- 未运行验证命令就声明完成。
- 没有 subagent 能力却声称完成了多 agent 分派。
- 子 agent 返回散文总结，没有 TaskResult/ReviewReport packet，就当作通过。

## 适用判定

满足任一条件，按重任务处理：

- 跨 2 个以上文件或 2 个以上模块。
- 用户目标、范围、验收、质量层级任一项不清楚。
- 涉及数据模型、权限、安全、发布、迁移、外部服务或破坏性操作。
- 需要多步计划、跨阶段验证或可恢复进度。
- 用户显式使用 `tdr-`、`task-driver` 或要求先计划/先澄清。

明显方案分叉指：不同方案会改变 API、数据模型、用户流程、依赖、验证方式、风险边界、交付范围或回滚方式。出现明显方案分叉时，必须在 spec 或 plan 阶段让用户拍板。

## 澄清分层

不要把所有澄清项都当成同等阻塞。

- **必填门禁**：Goal、Scope、Non-goals、Acceptance Criteria、Constraints、Quality Level。
- **按需补充**：User scenario、Risks、Trade-offs、Alternatives。只有经事实收集和影响判断确认不影响方案或验收时，才可标 `N/A`，并必须写明判断依据；否则必须补齐。
- **禁止伪闭合**：不能用“先按常规做”“后续再补”“大概即可”替代必填门禁。

## 单问题澄清门

禁止问卷式连续提 1 个以上问题。每次面向用户的澄清回复只能包含一个需要用户拍板的决策点。

规则：

- 如果同时缺少多个信息，先通过本地事实收集缩小不确定性；只能对低风险、可逆、行业惯例明确且不影响目标/范围/验收的细节使用默认值。
- 默认值必须显式标注为 `assumption`，写明依据和可回滚方式。
- 禁止对用户意图、业务目标、优先级、范围边界、质量层级、验收标准、发布/删除/迁移/权限/安全等决策使用默认值。
- 一旦默认值会影响 spec、plan、AC 或风险边界，必须作为单问题澄清项让用户拍板。
- 问题必须从宏观到细节推进：整体目标 → 大类/规划轴 → 范围切片 → 小项目/模块 → 行为细节 → 实现约束。
- 用户要求“重新规划 / 整体规划 / 重构规划 / 从头梳理 / 重新设计”时，第一问必须落在整体规划视角或大类划分，不得直接跳到文件、类名、接口、页面细节。
- 能给参考答案时，必须给 2-3 个互斥选项、各自结果和一个推荐选项；禁止只抛开放问题。
- 禁止借口“不能给参考答案”退回开放式提问。只有问题属于用户独占事实（例如私有业务目标、账号/权限、不可从仓库或上下文推断的偏好）时，才允许不给选项；这时也必须说明已查事实和为什么无法形成参考选项。
- 选项不是多个问题；每个选项只能回答同一个决策点。
- 禁止在一个回复中列出多个问号、多个“请确认”、多个“需要你决定”的条目。

澄清输出模板：

```markdown
**已知事实**：[用 1-3 句概括已查到的信息]
**当前层级**：[整体目标 / 大类划分 / 范围切片 / 小项目 / 行为细节 / 实现约束]
**只需要你拍板 1 个问题**：[一个决策问题]

**选项**：
1. [选项 A] -> [结果]
2. [选项 B] -> [结果]
3. [选项 C] -> [结果，可选]

**推荐**：[推荐选项]，因为 [理由]。
**下一步**：[选定后将继续做什么事实收集或下一层澄清]
```

## 品质层级

| 层级 | 验收差异 |
|---|---|
| MVP | 核心路径可用；有最小验证；允许明确记录的非关键边界缺口。 |
| 精打磨 | 覆盖主要边界、错误状态、空状态、回归检查；交互/文案/日志不粗糙。 |
| 生产级 | 覆盖安全、权限、性能、兼容、观测、回滚/迁移、完整回归；残余风险必须可接受或有明确 owner。 |

如果用户未指定质量层级，默认按“精打磨”规划。

只有同时满足以下条件，才可降为 MVP：

- 用户目标是诊断、探索、一次性脚本或临时数据整理。
- 不修改生产代码路径、公共 API、权限、安全、发布、迁移、依赖、构建配置或用户可见核心流程。
- 失败不会造成数据丢失、发布风险、权限风险或用户可见回归。
- 有明确的最小验证方式。
- 在 spec/plan 中记录降级原因和不覆盖的边界。

不满足任一条件时，不得降级，必须保持“精打磨”或询问用户是否接受 MVP。

## 工件

大任务创建：

- Spec：`docs/task-driver/specs/YYYY-MM-DD--slug.md`
- Plan：`docs/task-driver/plans/YYYY-MM-DD--slug.md`
- Ledger：`docs/task-driver/ledgers/YYYY-MM-DD--slug.md`

小任务可内联 spec/plan，但必须同时满足全部条件：

- 一轮内完成。
- 最多修改一个非关键文件。
- 不新增、删除、移动、重命名文件。
- 不改变数据模型、权限、安全、发布、迁移、依赖、构建配置、路由、公共 API、跨平台行为。
- 无明显方案分叉。
- 有明确验证命令或确定性检查方式。

只要触及关键文件或高风险行为，即使只改一个文件，也必须按大任务创建 spec/plan/ledger。

## 多 Agent 执行模式

多 agent 是增强路径，不是依赖项。只有当前环境明确提供 subagent/parallel agent 工具时才使用。执行模式选择必须写入 PlanPacket.mode，并记录选择理由。

- `single-agent`：仅在没有 subagent 工具，或任务低风险且单 agent review 足够时使用。当前 agent 顺序扮演 Brainstormer、Planner、Implementer、Reviewer、Verifier。
- `multi-agent-review`：当前环境有 subagent 工具且满足任一条件时必须优先使用：
  - 涉及安全、权限、数据、迁移、发布、依赖、构建配置、公共 API。
  - 跨 3 个以上文件或 2 个以上模块。
  - 用户明确要求 review、审查、验证、复核。
  - 任务失败成本高或回滚成本高。
- `multi-agent-parallel`：只有同时满足以下条件才允许使用：
  - 任务之间文件集合不重叠。
  - PlanPacket 已定义合并顺序、冲突处理和最终验证命令。
  - 每个并行任务都有独立 AC 或独立验证证据。
  - 有 controller 负责合并和最终 verification。

没有 subagent 时继续用 `single-agent`，不得阻塞任务，但必须在 plan/ledger 记录降级原因。无论哪种模式，都必须写结构化 packet。禁止声称完成了多 agent 分派。

## 中文显示名规范

面向用户输出时，优先使用中文显示名。首次出现英文协议标识、状态值、字段名、模式名或阶段名时，必须使用“中文显示名（英文标识）”格式；后续同一回复内可只用中文显示名。代码块、字段表、路径、JSON/YAML key、枚举值本身保持英文原值。

不得为了中文化修改机器契约本身：skill 名、文件路径、frontmatter key、JSON key、YAML key、字段名、枚举值、命令、代码块内容必须保持原值；只改变面向用户的显示方式。

示例：

- 需求规格交接包（SpecPacket）
- 计划交接包（PlanPacket）
- 任务结果（TaskResult）
- 用户验收门禁（User Acceptance Gate）
- 等待用户验收（`awaiting_user_acceptance`）

## 中英文对照表

| 英文标识 | 中文显示名 |
|---|---|
| Task Driver | 任务驱动框架 |
| task-driver | 任务驱动标识 |
| skill | 技能 |
| agent | 智能体 |
| workflow | 工作流 |
| task-management | 任务管理 |
| spec | 需求规格 |
| plan | 计划 |
| ledger | 执行台账 |
| packet | 交接包 |
| schema | 结构定义 |
| Brainstormer | 需求澄清者 |
| Planner | 计划制定者 |
| Implementer | 实现者 |
| Reviewer | 评审者 |
| Verifier | 验证者 |
| SpecPacket | 需求规格交接包 |
| PlanPacket | 计划交接包 |
| TaskResult | 任务结果 |
| ReviewReport | 评审报告 |
| VerificationReport | 验证报告 |
| approved | 已确认 |
| draft | 草稿 |
| superseded | 已被替代 |
| degraded-single-skill | 降级单技能模式 |
| mode | 执行模式 |
| single-agent | 单智能体模式 |
| multi-agent-review | 多智能体评审模式 |
| multi-agent-parallel | 多智能体并行模式 |
| subagent | 子智能体 |
| parallel agent | 并行智能体 |
| review gate | 评审门禁 |
| verification gate | 验证门禁 |
| User Acceptance Gate | 用户验收门禁 |
| Scope Drift Detector | 范围漂移检测器 |
| File Map | 文件映射 |
| Iteration Log | 迭代记录 |
| Plan Revision Protocol | 计划修订协议 |
| Diff From | 相比上一版差异 |
| Single Source of Truth | 单一事实源 |
| Cross-Packet References | 交接包跨引用 |
| quality level | 质量层级 |
| MVP | 最小可用版 |
| Polished | 精打磨 |
| Production-grade | 生产级 |
| Why | 目的 |
| What | 交付内容 |
| Success | 成功标准 |
| Quality | 质量要求 |
| Scope | 范围 |
| Constraints | 约束 |
| User scenario | 用户场景 |
| Trade-offs | 取舍 |
| Risks | 风险 |
| Alternatives | 备选方案 |
| Goal | 目标 |
| Non-Goals | 非目标 |
| Proposed Design | 建议方案 |
| Alternatives Considered | 已考虑的备选方案 |
| Acceptance Criteria | 验收标准 |
| Implementation Plan | 实施计划 |
| Global Constraints | 全局约束 |
| Interfaces | 接口 |
| Tasks | 任务 |
| Task | 任务 |
| Owner role | 负责人角色 |
| Files | 文件 |
| Acceptance | 验收项 |
| Status | 状态 |
| Predecessor | 前序版本 |
| Run | 运行命令 |
| Expected | 预期结果 |
| Actual | 实际结果 |
| Evidence | 证据 |
| evidence_strength | 证据强度 |
| strong | 强证据 |
| medium | 中等证据 |
| weak | 弱证据 |
| stale | 过期证据 |
| blocked | 受阻 |
| partial | 部分完成 |
| not_met | 未满足 |
| met | 已满足 |
| awaiting_user_acceptance | 等待用户验收 |
| accepted_by_user | 用户已接受 |
| rejected_by_user | 用户已拒绝 |
| pending | 待处理 |
| in_progress | 进行中 |
| done | 已完成 |
| pass | 通过 |
| fail | 失败 |
| needs_fix | 需要修复 |
| Critical | 严重 |
| Important | 重要 |
| Minor | 次要 |
| backlog | 待办积压 |

## 结构化交接 Packet

Packet schema 单点定义在本节。子阶段只声明本阶段产出哪种 packet，不重复 schema。

旧版 YAML 示例升级为字段表（保留 YAML 作为简表，置于字段表之后）。新字段为本次升级增量；旧字段保留，向后兼容。

### SpecPacket

| Field | Type | Required | Enum | Description |
|---|---|---|---|---|
| spec_path | string | yes | - | spec 文件路径 |
| goal | string | yes | - | 一句话目标 |
| acceptance_criteria | array<object> | yes | - | 元素含 `{id: AC-N, description, verification}`；id 必填且唯一 |
| constraints | array<string> | yes | - | 精确约束 |
| quality_level | enum | yes | mvp / polished / production | 见“品质层级” |
| approved_by_user | bool | yes | true / false | 必须为 true 才能进入 planning |
| status | enum | yes | draft / approved / superseded | 见“Packet Status & Transitions” |

### PlanPacket

| Field | Type | Required | Enum | Description |
|---|---|---|---|---|
| plan_path | string | yes | - | plan 文件路径 |
| ledger_path | string | yes | - | ledger 文件路径 |
| plan_version | string | yes | v1 / v2 / ... | 见“Plan Revision Protocol” |
| predecessor | string | no | - | 前序 plan 路径；首版填“无” |
| mode | enum | yes | single-agent / multi-agent-review / multi-agent-parallel / degraded-single-skill | 执行模式 |
| tasks | array<object> | yes | - | 元素含 `{id: T-NNN, owner_role, objective, files, verification, acceptance_ac_ids}`；id 必填且唯一 |
| stop_conditions | array<string> | yes | - | 触发停机的条件 |
| status | enum | yes | draft / approved / superseded | 同上 |

### TaskResult

| Field | Type | Required | Enum | Description |
|---|---|---|---|---|
| task_id | string | yes | T-NNN | 必须引用 PlanPacket.tasks[].id |
| status | enum | yes | pending / in_progress / done / blocked / partial | 见状态机 |
| files_changed | array<string> | yes | - | 改动文件路径；用于 Scope Drift Detector |
| commands_run | array<string> | yes | - | 实际运行的命令 |
| evidence | array<object> | yes | - | 证据列表，结构见 ledger Evidence 段 |
| ac_coverage | array<object> | yes | - | 元素 `{ac_id: AC-N, covered: full / partial / none, evidence}`；ac_id 必须引用 SpecPacket.acceptance_criteria[].id；每个任务必须列出 plan 中 acceptance_ac_ids 的覆盖情况，未覆盖也必须写 `covered: none` 和原因 |
| deviations_from_plan | array<string> | no | - | 偏离 plan 的内容；漂移触发停机回问 |

### ReviewReport

| Field | Type | Required | Enum | Description |
|---|---|---|---|---|
| task_id | string | yes | T-NNN | 必须引用 TaskResult.task_id |
| status | enum | yes | pass / needs_fix / blocked | 见状态机 |
| findings | array<object> | yes | - | 元素 `{severity: critical / important / minor, file, issue, required_fix}` |

### VerificationReport

| Field | Type | Required | Enum | Description |
|---|---|---|---|---|
| status | enum | yes | met / partial / not_met / blocked / awaiting_user_acceptance / accepted_by_user / rejected_by_user | 见状态机 |
| mode | enum | yes | single-agent / multi-agent-review / multi-agent-parallel / degraded-single-skill | 与 plan 一致 |
| coverage | array<object> | yes | - | 元素 `{ac_id: AC-N, evidence_ref, evidence_strength, status: met / partial / not_met / blocked}`；ac_id 必须引用 SpecPacket.acceptance_criteria[].id |
| unmet_requirements | array<object> | yes | - | 元素 `{ac_id, reason, next_action}` |
| delivery_acknowledged_by_user | enum | yes | true / false / partial / pending | User Acceptance Gate 状态；VerificationReport 初次写入必须为 `pending`，用户回复后更新为 `true / false / partial` |

### YAML 简表（仅作示例参考，字段语义以上方字段表为准）

```yaml
mode: single-agent | multi-agent-review | multi-agent-parallel | degraded-single-skill
spec_packet: { spec_path, goal, acceptance_criteria[id, description, verification], constraints, quality_level, approved_by_user, status }
plan_packet: { plan_path, ledger_path, plan_version, predecessor, mode, tasks[id: T-NNN, owner_role, objective, files, verification, acceptance_ac_ids], stop_conditions, status }
task_result: { task_id: T-NNN, status, files_changed, commands_run, evidence, ac_coverage[ac_id, covered, evidence], deviations_from_plan }
review_report: { task_id: T-NNN, status, findings[severity, file, issue, required_fix] }
verification_report: { status, mode, coverage[ac_id, evidence_ref, evidence_strength, status], unmet_requirements[ac_id, reason, next_action], delivery_acknowledged_by_user }
```

在 `single-agent` 模式下，把 packet 写入 ledger。  
在多 agent 模式下，packet 是唯一交接输入输出；禁止用散文摘要替代。

Packet schema 单点定义是刻意设计：主控负责字段契约，子阶段只声明产出类型和必填信息，避免多处 schema 漂移。

TaskResult.ac_coverage 为必填；不得以“本任务未覆盖 AC”为由省略字段。

VerificationReport.delivery_acknowledged_by_user 为必填；未进入 User Acceptance Gate 前必须显式写 `pending`。

## Packet Status & Transitions

Status 枚举与合法迁移：

- **SpecPacket**：`draft → approved → superseded`。`approved` 是进入 planning 的前置条件；`superseded` 由后续新 spec 替换。
- **PlanPacket**：`draft → approved → superseded`。`approved` 是进入 executing 的前置条件；plan-revision 触发 `approved → superseded` 并产生新 plan v2。
- **TaskResult**：`pending → in_progress → done | blocked | partial`。`done` 进入 review；`blocked` / `partial` 需 ledger 写明原因并触发循环退出判定。
- **ReviewReport**：`pass | needs_fix | blocked`。`needs_fix` 必须先修后复审，否则不得继续下一个任务；Critical / Important findings 阻塞继续。
- **VerificationReport**：`met | partial | not_met | blocked → awaiting_user_acceptance → accepted_by_user | rejected_by_user`。所有 AC 至少 Met/Partial 后进入 `awaiting_user_acceptance`；用户 accept 后进入 `accepted_by_user`，用户 reject 后进入 `rejected_by_user`，详见 verification SKILL.md 的 User Acceptance Gate。

非法迁移视为协议违规：例如 SpecPacket 直接从 `draft` 标 `superseded`、TaskResult 跳过 `in_progress` 标 `done`、VerificationReport 跳过 `awaiting_user_acceptance` 直接标 `accepted_by_user`。

## Cross-Packet References

Packet 之间必须以 ID 引用，不得用散文/位置/标题模糊指代：

- TaskResult.task_id → PlanPacket.tasks[].id（`T-NNN`）。
- TaskResult.ac_coverage[].ac_id → SpecPacket.acceptance_criteria[].id（`AC-N`）。
- ReviewReport.task_id → TaskResult.task_id。
- VerificationReport.coverage[].ac_id → SpecPacket.acceptance_criteria[].id。

引用断链（例如 TaskResult 的 task_id 在 PlanPacket 找不到、ac_coverage 引用了不存在的 AC）必须在 review gate 拦截，视为 needs_fix。

## Single Source of Truth: PlanPacket

任务清单存在两种表达：PlanPacket.tasks[]（结构化）与 plan markdown 的 `### Task T-NNN` 段落（可读）。两者必须一一对应。

规则：

- **PlanPacket.tasks[] 是权威单源**。plan markdown 任务条目视为 packet 的人类可读渲染。
- 任意字段（id、files、acceptance、verification）漂移时，**以 packet 为准**，并立即同步 markdown。
- 任务的新增 / 删除 / 重排必须先改 packet，再改 markdown，禁止反向。
- planning 自检门禁负责一一对应校验；executing 阶段读 PlanPacket，不读 markdown 描述。
- ledger 中 Status 段每个任务行必须用 `T-NNN` 引用 packet。

## 证据强度

验证证据必须标注强度：

- `strong`：新鲜运行结果或直接检查目标产物，覆盖对应验收标准。
- `medium`：覆盖核心路径但缺少部分边界；只能标 `Partial`，并必须写 caveat、缺口、影响范围和补强验证命令。
- `weak`：只看 diff、只读代码、只跑窄检查或证据间接；不能支撑完成声明。
- `stale`：旧会话、旧日志、旧测试结果；不能支撑完成声明。

验收状态规则：

- 只有 `strong` 可标 `Met`。
- `medium` 最多标 `Partial`，并写清缺口。
- `weak` 或 `stale` 必须标 `Not met` 或 `Blocked`。

Partial 仅在同时满足以下条件时可进入 User Acceptance Gate：

- 核心用户路径或核心目标已被 strong 或 medium 证据覆盖。
- 未覆盖部分不涉及安全、权限、数据、迁移、发布、依赖、构建配置、公共 API。
- 未覆盖部分不会造成主要流程不可用或用户可见严重回归。
- VerificationReport.unmet_requirements[] 已列出缺口、原因、next_action。
- 最终报告明确提示用户这是 partial 交付，并请求 accept / reject / partial-accept。

否则 Partial 不得进入 User Acceptance Gate，必须回到 executing、blocked 或 plan-revision。

## Red Flags

出现这些信号时，必须回退到执行或验证，不得继续包装成完成：

- “应该好了”“看起来没问题”“理论上会过”。
- 只看 diff，没有运行命令或检查产物。
- 只运行窄测试，却宣称整体完成。
- 使用旧测试结果或旧日志。
- 验证没有覆盖某条 acceptance criterion。
- 跳过失败测试直接实现行为变化。
- 反复修同一 requirement 但不记录尝试和退出条件。

## TDD 例外

功能、bugfix、行为变化必须先写失败测试。

只有以下情况可不写失败测试：

- 用户明确豁免。
- 任务是纯文档、纯注释、纯静态文案，且不改变运行行为。
- 当前项目没有可运行测试框架，且无法在本轮安全补充测试框架。
- 目标行为只能通过人工验收或外部系统验证，无法构造自动化测试。

不写失败测试时必须：

- 在 spec/plan/ledger 记录豁免原因。
- 写明替代验证方式。
- 标注对应 AC 的 evidence_strength 上限。
- 若替代验证不能达到 strong，不得将对应 AC 标为 Met。

## 流程

1. **事实收集**：先读文件、文档、git、日志、已有计划和当前行为。
2. **澄清**：禁止问卷式连续提问；每轮只问一个最高影响决策，先闭合 Why、范围、成功标准、非目标、约束、质量层级。
3. **Spec 确认**：保存 approved spec，自检无占位、矛盾、模糊验收和范围过大。
4. **Plan 确认**：写清文件、接口、任务、测试、命令、预期结果、停机条件。
5. **执行**：按 plan 连续推进；行为变化优先 TDD；每个任务更新 ledger。
6. **评审**：每个 PlanPacket.tasks[] 中的任务都必须执行 Review Gate；按风险调整深度，但不得跳过。Critical/Important 必须修复。
7. **验证**：运行能证明最终声明的命令，汇报证据、缺口、残余风险。

## 执行-验证循环退出

同一 requirement 的执行-验证循环最多 2 轮。每轮必须在 ledger 的 `## Iteration Log` 段写入一条记录，字段：`attempt / requirement_id / hypothesis / command / result / next_assumption / outcome`。

第 2 轮后仍失败时，必须停止循环并进入以下之一：

- `blocked`：需要用户决策、权限、环境、外部服务或范围调整。
- `partial`：核心目标满足但存在用户可接受的明确缺口。
- `plan-revision`：原 plan 假设错误，需要回到 plan 阶段，按 Plan Revision Protocol 升级 plan_version。

不得无限“修一下再测一下”。如果根因未知，状态必须是 `blocked` 或 `plan-revision`。

## Plan Revision Protocol

触发条件：执行-验证循环 2 轮仍失败、或执行中发现 plan 假设错误（接口、依赖、范围）。

规则：

- spec 仍正确：只升级 plan，`plan_version` 递增（v1 → v2），`predecessor` 指向前一版 plan 路径，新 plan 顶部新增 `## Diff From v[N-1]` 段简述结构性差异；前一版状态置 `superseded`。
- spec 也错误：必须回到 brainstorming 写新 spec，旧 spec 状态置 `superseded`，再产出新 plan v1。
- plan-revision 必须取得用户对新 plan 的 approve；不得在用户未确认前继续执行。

## User Acceptance Gate（钩子）

VerificationReport 写完且所有 AC 至少 Met/Partial 后，状态进入 `awaiting_user_acceptance`，触发 verification SKILL.md 定义的 User Acceptance Gate；用户回复后状态变为 `accepted_by_user`。该门只在最终触发一次，不与“已确认 plan 后不得每步讨确认”冲突。

## 停机回问

只在这些情况停下问用户：

- plan 存在关键缺口或矛盾。
- 任务超出 approved scope。
- 需要用户拥有的业务决策。
- 验证反复失败且根因未知。
- 继续会删除、覆盖、发布、合并或丢弃工作。

## 错误提示模板

遇到异常时，必须使用结构化模板输出提示，确保用户能快速定位问题类型、原因和下一步动作。完整模板见 `references/error-templates.md`。

适用关系：

- 停机回问：所有阶段。
- 验证失败：verification。
- 循环退出：executing / verification。
- 范围漂移：executing。
- 阻塞状态：所有阶段。

## 结束报告

包含：

- 改了什么。
- 创建或更新的 spec/plan/ledger。
- 验证命令和结果。
- approved acceptance criteria 是否满足。
- 残余风险或后续 backlog。
