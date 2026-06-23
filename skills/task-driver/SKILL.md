---
name: task-driver
description: "重任务总控。用于 tdr-、task-driver、模糊任务、跨文件修改、需要 spec/plan/ledger、连续执行、TDD、review gate、verification gate、可选多 agent 与单 agent 降级的场景。"
---

# Task Driver

你是重任务总控。你的职责是按阶段推进任务：先消除不确定性，再连续执行，最后用证据证明完成。

## 阶段 Skill

按顺序使用：

1. `task-driver-brainstorming`：事实收集、深度澄清、方案比较、产出 spec。
2. `task-driver-planning`：实施计划、任务拆解、验证命令、创建 ledger。
3. `task-driver-executing`：按 plan 连续执行、TDD、任务评审、更新 ledger。
4. `task-driver-verification`：最终验收、证据审计、残余风险。

如果某个阶段 skill 不可用，仍按同一契约在当前 skill 内执行，不得跳过阶段。

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
- **按需补充**：User scenario、Risks、Trade-offs、Alternatives。影响方案或验收时必须补齐；不影响时可标 `N/A` 并说明原因。
- **禁止伪闭合**：不能用“先按常规做”“后续再补”“大概即可”替代必填门禁。

## 品质层级

| 层级 | 验收差异 |
|---|---|
| MVP | 核心路径可用；有最小验证；允许明确记录的非关键边界缺口。 |
| 精打磨 | 覆盖主要边界、错误状态、空状态、回归检查；交互/文案/日志不粗糙。 |
| 生产级 | 覆盖安全、权限、性能、兼容、观测、回滚/迁移、完整回归；残余风险必须可接受或有明确 owner。 |

如果用户未指定质量层级，默认按“精打磨”规划；若任务明显是临时排查或一次性脚本，可降为 MVP，但必须写明原因。

## 工件

大任务创建：

- Spec：`docs/task-driver/specs/YYYY-MM-DD--slug.md`
- Plan：`docs/task-driver/plans/YYYY-MM-DD--slug.md`
- Ledger：`docs/task-driver/ledgers/YYYY-MM-DD--slug.md`

小任务可内联 spec/plan，但必须满足：一轮内完成、最多一个文件、无明显方案分叉、有明确验证命令。

## 多 Agent 执行模式

多 agent 是增强路径，不是依赖项。只有当前环境明确提供 subagent/parallel agent 工具时才使用。

- `single-agent`：默认模式。当前 agent 顺序扮演 Brainstormer、Planner、Implementer、Reviewer、Verifier。
- `multi-agent-review`：有 subagent 时，把 Reviewer 或 Verifier 派给独立 agent。
- `multi-agent-parallel`：只有任务独立、plan 已定义合并和验证规则时，才并行派发 Implementer。

没有 subagent 时继续用 `single-agent`，不得阻塞任务。无论哪种模式，都必须写结构化 packet。

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
| mode | enum | yes | single-agent / multi-agent-review / multi-agent-parallel | 执行模式 |
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
| ac_coverage | array<object> | no | - | 元素 `{ac_id: AC-N, covered: full / partial / none, evidence}`；ac_id 必须引用 SpecPacket.acceptance_criteria[].id |
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
| status | enum | yes | met / partial / not_met / blocked / awaiting_user_acceptance / accepted_by_user | 见状态机 |
| mode | enum | yes | single-agent / multi-agent-review / multi-agent-parallel | 与 plan 一致 |
| coverage | array<object> | yes | - | 元素 `{ac_id: AC-N, evidence_ref, evidence_strength, status: met / partial / not_met / blocked}`；ac_id 必须引用 SpecPacket.acceptance_criteria[].id |
| unmet_requirements | array<object> | yes | - | 元素 `{ac_id, reason, next_action}` |
| delivery_acknowledged_by_user | enum | no | true / false / partial / pending | 见 verification SKILL.md 的 User Acceptance Gate |

### YAML 简表（仅作示例参考，字段语义以上方字段表为准）

```yaml
mode: single-agent | multi-agent-review | multi-agent-parallel
spec_packet: { spec_path, goal, acceptance_criteria[id, description, verification], constraints, quality_level, approved_by_user, status }
plan_packet: { plan_path, ledger_path, plan_version, predecessor, mode, tasks[id: T-NNN, owner_role, objective, files, verification, acceptance_ac_ids], stop_conditions, status }
task_result: { task_id: T-NNN, status, files_changed, commands_run, evidence, ac_coverage[ac_id, covered, evidence], deviations_from_plan }
review_report: { task_id: T-NNN, status, findings[severity, file, issue, required_fix] }
verification_report: { status, mode, coverage[ac_id, evidence_ref, evidence_strength, status], unmet_requirements[ac_id, reason, next_action], delivery_acknowledged_by_user }
```

在 `single-agent` 模式下，把 packet 写入 ledger。  
在多 agent 模式下，packet 是唯一交接输入输出；禁止用散文摘要替代。

Packet schema 单点定义是刻意设计：主控负责字段契约，子阶段只声明产出类型和必填信息，避免多处 schema 漂移。

## Packet Status & Transitions

Status 枚举与合法迁移：

- **SpecPacket**：`draft → approved → superseded`。`approved` 是进入 planning 的前置条件；`superseded` 由后续新 spec 替换。
- **PlanPacket**：`draft → approved → superseded`。`approved` 是进入 executing 的前置条件；plan-revision 触发 `approved → superseded` 并产生新 plan v2。
- **TaskResult**：`pending → in_progress → done | blocked | partial`。`done` 进入 review；`blocked` / `partial` 需 ledger 写明原因并触发循环退出判定。
- **ReviewReport**：`pass | needs_fix | blocked`。`needs_fix` 必须先修后复审，否则不得继续下一个任务；Critical / Important findings 阻塞继续。
- **VerificationReport**：`met | partial | not_met | blocked → awaiting_user_acceptance → accepted_by_user`。所有 AC 至少 Met/Partial 后进入 `awaiting_user_acceptance`，用户回复后进入 `accepted_by_user`，详见 verification SKILL.md 的 User Acceptance Gate。

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
- `medium`：覆盖核心路径但缺少部分边界；可用于部分通过，但必须写 caveat。
- `weak`：只看 diff、只读代码、只跑窄检查或证据间接；不能支撑完成声明。
- `stale`：旧会话、旧日志、旧测试结果；不能支撑完成声明。

验收状态规则：

- 只有 `strong` 可标 `Met`。
- `medium` 最多标 `Partial`，并写清缺口。
- `weak` 或 `stale` 必须标 `Not met` 或 `Blocked`。

## Red Flags

出现这些信号时，必须回退到执行或验证，不得继续包装成完成：

- “应该好了”“看起来没问题”“理论上会过”。
- 只看 diff，没有运行命令或检查产物。
- 只运行窄测试，却宣称整体完成。
- 使用旧测试结果或旧日志。
- 验证没有覆盖某条 acceptance criterion。
- 跳过失败测试直接实现行为变化。
- 反复修同一 requirement 但不记录尝试和退出条件。

## 流程

1. **事实收集**：先读文件、文档、git、日志、已有计划和当前行为。
2. **澄清**：一次只问一个关键问题，先闭合 Why、范围、成功标准、非目标、约束、质量层级。
3. **Spec 确认**：保存 approved spec，自检无占位、矛盾、模糊验收和范围过大。
4. **Plan 确认**：写清文件、接口、任务、测试、命令、预期结果、停机条件。
5. **执行**：按 plan 连续推进；行为变化优先 TDD；每个任务更新 ledger。
6. **评审**：每个有意义任务检查 spec compliance 和质量问题，Critical/Important 必须修复。
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

## 结束报告

包含：

- 改了什么。
- 创建或更新的 spec/plan/ledger。
- 验证命令和结果。
- approved acceptance criteria 是否满足。
- 残余风险或后续 backlog。
