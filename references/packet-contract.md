# Packet Contract

Packet schema 单点定义在本文。阶段参考只声明本阶段产出哪种 packet，不重复 schema。

## SpecPacket

| Field | Type | Required | Enum | Description |
|---|---|---|---|---|
| spec_path | string | yes | - | spec 文件路径 |
| goal | string | yes | - | 一句话目标 |
| acceptance_criteria | array<object> | yes | - | 元素含 `{id: AC-N, description, verification}`；id 必填且唯一 |
| constraints | array<string> | yes | - | 精确约束 |
| quality_level | enum | yes | mvp / polished / production | 见品质层级 |
| approved_by_user | bool | yes | true / false | 必须为 true 才能进入 planning |
| status | enum | yes | draft / approved / superseded | 见 Packet Status & Transitions |

## PlanPacket

| Field | Type | Required | Enum | Description |
|---|---|---|---|---|
| plan_path | string | yes | - | plan 文件路径 |
| ledger_path | string | yes | - | ledger 文件路径 |
| plan_version | string | yes | v1 / v2 / ... | 见 Plan Revision Protocol |
| predecessor | string | no | - | 前序 plan 路径；首版填“无” |
| mode | enum | yes | single-agent / multi-agent-review / multi-agent-parallel / degraded-single-skill | 执行模式 |
| tasks | array<object> | yes | - | 元素含 `{id: T-NNN, owner_role, objective, files, verification, acceptance_ac_ids}`；id 必填且唯一 |
| stop_conditions | array<string> | yes | - | 触发停机的条件 |
| status | enum | yes | draft / approved / superseded | 同上 |

## TaskResult

| Field | Type | Required | Enum | Description |
|---|---|---|---|---|
| task_id | string | yes | T-NNN | 必须引用 PlanPacket.tasks[].id |
| status | enum | yes | pending / in_progress / done / blocked / partial | 见状态机 |
| files_changed | array<string> | yes | - | 改动文件路径；用于 Scope Drift Detector |
| commands_run | array<string> | yes | - | 实际运行的命令 |
| evidence | array<object> | yes | - | 证据列表，结构见 ledger Evidence 段 |
| ac_coverage | array<object> | yes | - | 元素 `{ac_id: AC-N, covered: full / partial / none, evidence}`；ac_id 必须引用 SpecPacket.acceptance_criteria[].id；每个任务必须列出 plan 中 acceptance_ac_ids 的覆盖情况，未覆盖也必须写 `covered: none` 和原因 |
| deviations_from_plan | array<string> | no | - | 偏离 plan 的内容；漂移触发停机回问 |

## ReviewReport

| Field | Type | Required | Enum | Description |
|---|---|---|---|---|
| task_id | string | yes | T-NNN | 必须引用 TaskResult.task_id |
| status | enum | yes | pass / needs_fix / blocked | 见状态机 |
| findings | array<object> | yes | - | 元素 `{severity: critical / important / minor, file, issue, required_fix}` |

## VerificationReport

| Field | Type | Required | Enum | Description |
|---|---|---|---|---|
| status | enum | yes | met / partial / not_met / blocked / awaiting_user_acceptance / accepted_by_user / rejected_by_user | 见状态机 |
| mode | enum | yes | single-agent / multi-agent-review / multi-agent-parallel / degraded-single-skill | 与 plan 一致 |
| coverage | array<object> | yes | - | 元素 `{ac_id: AC-N, evidence_ref, evidence_strength, status: met / partial / not_met / blocked}`；ac_id 必须引用 SpecPacket.acceptance_criteria[].id |
| unmet_requirements | array<object> | yes | - | 元素 `{ac_id, reason, next_action}` |
| delivery_acknowledged_by_user | enum | yes | true / false / partial / pending | User Acceptance Gate 状态；VerificationReport 初次写入必须为 `pending`，用户回复后更新为 `true / false / partial` |
| quality_score | object | no | - | 质量评分；结构见 `references/quality-rubric.md`，未评分时写 `{overall: N/A, rationale}` |

## YAML Summary

```yaml
mode: single-agent | multi-agent-review | multi-agent-parallel | degraded-single-skill
spec_packet: { spec_path, goal, acceptance_criteria[id, description, verification], constraints, quality_level, approved_by_user, status }
plan_packet: { plan_path, ledger_path, plan_version, predecessor, mode, tasks[id: T-NNN, owner_role, objective, files, verification, acceptance_ac_ids], stop_conditions, status }
task_result: { task_id: T-NNN, status, files_changed, commands_run, evidence, ac_coverage[ac_id, covered, evidence], deviations_from_plan }
review_report: { task_id: T-NNN, status, findings[severity, file, issue, required_fix] }
verification_report: { status, mode, coverage[ac_id, evidence_ref, evidence_strength, status], unmet_requirements[ac_id, reason, next_action], delivery_acknowledged_by_user, quality_score }
```

在 `single-agent` 模式下，把 packet 写入 ledger。在多 agent 模式下，packet 是唯一交接输入输出；禁止用散文摘要替代。

TaskResult.ac_coverage 为必填；不得以“本任务未覆盖 AC”为由省略字段。VerificationReport.delivery_acknowledged_by_user 为必填；未进入 User Acceptance Gate 前必须显式写 `pending`。

## Packet Status & Transitions

- **SpecPacket**：`draft -> approved -> superseded`。`approved` 是进入 planning 的前置条件。
- **PlanPacket**：`draft -> approved -> superseded`。`approved` 是进入 executing 的前置条件。
- **TaskResult**：`pending -> in_progress -> done | blocked | partial`。`done` 进入 review。
- **ReviewReport**：`pass | needs_fix | blocked`。`needs_fix` 必须先修后复审，否则不得继续下一个任务。
- **VerificationReport**：`met | partial | not_met | blocked -> awaiting_user_acceptance -> accepted_by_user | rejected_by_user`。

非法迁移视为协议违规：例如 SpecPacket 直接从 `draft` 标 `superseded`、TaskResult 跳过 `in_progress` 标 `done`、VerificationReport 跳过 `awaiting_user_acceptance` 直接标 `accepted_by_user`。

## Cross-Packet References

Packet 之间必须以 ID 引用，不得用散文、位置或标题模糊指代：

- TaskResult.task_id -> PlanPacket.tasks[].id (`T-NNN`)。
- TaskResult.ac_coverage[].ac_id -> SpecPacket.acceptance_criteria[].id (`AC-N`)。
- ReviewReport.task_id -> TaskResult.task_id。
- VerificationReport.coverage[].ac_id -> SpecPacket.acceptance_criteria[].id。

引用断链必须在 Review Gate 拦截，视为 `needs_fix`。

## Single Source of Truth: PlanPacket

PlanPacket.tasks[] 是任务清单权威单源；plan markdown 的 `### Task T-NNN` 段落只是人类可读渲染。

- 任意字段漂移时，以 packet 为准，并立即同步 markdown。
- 任务新增、删除、重排必须先改 packet，再改 markdown。
- planning 自检门禁负责一一对应校验；executing 阶段读 PlanPacket，不读 markdown 描述。
- ledger 中 Status 段每个任务行必须用 `T-NNN` 引用 packet。

## Evidence Strength

- `strong`：新鲜运行结果或直接检查目标产物，覆盖对应验收标准。
- `medium`：覆盖核心路径但缺少部分边界；只能标 `Partial`，并必须写 caveat、缺口、影响范围和补强验证命令。
- `weak`：只看 diff、只读代码、只跑窄检查或证据间接；不能支撑完成声明。
- `stale`：旧会话、旧日志、旧测试结果；不能支撑完成声明。

只有 `strong` 可标 `Met`；`medium` 最多 `Partial`；`weak` 或 `stale` 必须标 `Not met` 或 `Blocked`。
