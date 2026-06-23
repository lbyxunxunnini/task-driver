# Task Driver Loop & Handoff Upgrade Implementation Plan

**Spec:** docs/task-driver/specs/2026-06-23--task-driver-loop-and-handoff-upgrade.md
**Ledger:** docs/task-driver/ledgers/2026-06-23--task-driver-loop-and-handoff-upgrade.md
**Mode:** single-agent
**Quality level:** Polished
**Status:** Approved
**Plan version:** v1
**Predecessor:** （首版，无前序）

## Goal

按 11 条补丁升级 5 个子 skill + 1 个根 skill + CHANGELOG，使 packet 流式化、循环可驱动、目标可增量打点、交付有用户验收门。

## Global Constraints

- markdown-only，不引入代码。
- 旧 packet 字段保留，新字段增量。
- 任意单份 SKILL.md 单独可运转。
- 中文叙述。
- 不破坏 5 阶段 / 2 轮循环 / 品质三档 / 反例门禁。

## File Map

- Modify: `skills/task-driver/SKILL.md` — packet 字段表、状态机、引用规则、单源条款、验收门钩子
- Modify: `skills/task-driver-brainstorming/SKILL.md` — AC ID 强制
- Modify: `skills/task-driver-planning/SKILL.md` — Task ID + iteration_log + Evidence 结构化 + plan-revision 字段
- Modify: `skills/task-driver-executing/SKILL.md` — Scope Drift 检查 + ac_coverage
- Modify: `skills/task-driver-verification/SKILL.md` — User Acceptance Gate
- Modify: `SKILL.md` — 同步契约要点
- Modify: `CHANGELOG.md` — v0.4.3 条目

## Interfaces

- **Packet schema 表**：表头 `Field | Type | Required | Enum | Description`，主控 SKILL.md 单点定义。
- **Task ID 格式**：`T-001`、`T-002`，三位数字，左零填充。
- **AC ID 格式**：`AC-1`、`AC-2`。
- **Packet status 枚举**：
  - SpecPacket: `draft | approved | superseded`
  - PlanPacket: `draft | approved | superseded`
  - TaskResult: `pending | in_progress | done | blocked | partial`
  - ReviewReport: `pass | needs_fix | blocked`
  - VerificationReport: `met | partial | not_met | blocked | awaiting_user_acceptance | accepted_by_user`
- **跨引用字段**：
  - TaskResult.task_id → PlanPacket.tasks[].id
  - TaskResult.ac_coverage[].ac_id → SpecPacket.acceptance_criteria[].id
  - ReviewReport.task_id → TaskResult.task_id
  - VerificationReport.coverage[].ac_id → SpecPacket.acceptance_criteria[].id

## Tasks

### Task T-001: B1 主控 packet 字段表正式化
**Owner role:** Implementer
**Files:** `skills/task-driver/SKILL.md`
**Acceptance:** AC-1
**Review gate:** spec compliance + 字段完整性

- [ ] 把第 91-129 行 YAML 示例升级为 5 张字段表。
- [ ] 每张表含 Field/Type/Required/Enum/Description 五列。
- [ ] 保留原 YAML 作为简要示例，置于字段表之后。
- [ ] 写 TaskResult/ReviewReport 到 ledger。

### Task T-002: B2 Task ID 唯一锁定
**Owner role:** Implementer
**Files:** `skills/task-driver/SKILL.md`、`skills/task-driver-planning/SKILL.md`
**Acceptance:** AC-2
**Review gate:** ID 引用一致性

- [ ] 主控字段表 PlanPacket.tasks[] 增加 `id` 字段（必填，`T-NNN`）。
- [ ] TaskResult 字段表 `task_id` 类型注为 `T-NNN`，必填，引用 PlanPacket.tasks[].id。
- [ ] ReviewReport 字段表 `task_id` 同上。
- [ ] planning Plan 模板任务标题改为 `### Task T-001: [名称]`。

### Task T-003: B3 Packet 状态机
**Owner role:** Implementer
**Files:** `skills/task-driver/SKILL.md`
**Acceptance:** AC-3
**Review gate:** 枚举与迁移合法性

- [ ] 主控新增段落 "Packet Status & Transitions"。
- [ ] 列出 5 种 packet 的 status 枚举（按 Interfaces 章定义）。
- [ ] 列出每种 packet 的合法迁移路径（如 SpecPacket: draft → approved → superseded）。
- [ ] VerificationReport 包含 `awaiting_user_acceptance` 与 `accepted_by_user` 两个状态，为 A2 预留接口。

### Task T-004: B4 跨 packet 引用规则
**Owner role:** Implementer
**Files:** `skills/task-driver/SKILL.md`
**Acceptance:** AC-2（部分）+ 字段表覆盖
**Review gate:** 引用闭环

- [ ] 主控新增段落 "Cross-Packet References"。
- [ ] 列出 4 条引用规则（按 Interfaces 章定义）。
- [ ] 字段表中相应字段在 Description 列写明引用目标。

### Task T-005: B5 Evidence 子结构化
**Owner role:** Implementer
**Files:** `skills/task-driver-planning/SKILL.md`
**Acceptance:** AC-10
**Review gate:** 字段完整 + 与 verification 证据强度对齐

- [ ] Ledger 模板 Evidence 段升级为列表项对象格式：`- timestamp / command / exit_code / output_excerpt / covers_requirement_ids / strength`。
- [ ] 添加示例条目。
- [ ] strength 取值与 verification 阶段（strong/medium/weak/stale）对齐。

### Task T-006: B6 PlanPacket 单源化条款
**Owner role:** Implementer
**Files:** `skills/task-driver/SKILL.md`、`skills/task-driver-planning/SKILL.md`
**Acceptance:** AC-11
**Review gate:** 单源规则可执行

- [ ] 主控新增段落 "Single Source of Truth: PlanPacket"。
- [ ] 明示 PlanPacket.tasks[] 为权威，plan markdown 任务清单为渲染产物。
- [ ] 漂移裁定规则：以 packet 为准，发现漂移需立即同步 markdown。
- [ ] planning SKILL.md 自检门禁增加一条："plan markdown 任务条目必须与 PlanPacket.tasks[] 一一对应（id、files、acceptance）"。

### Task T-007: A3 AC 增量打点
**Owner role:** Implementer
**Files:** `skills/task-driver-brainstorming/SKILL.md`、`skills/task-driver-executing/SKILL.md`、`skills/task-driver/SKILL.md`
**Acceptance:** AC-4 + AC-5
**Review gate:** AC ID 链路闭环

- [ ] brainstorming Spec 模板 Acceptance Criteria 段示例改为表格 `| AC-N | 描述 | 验证方式 |`。
- [ ] brainstorming 必填门禁增加 "AC 必须以 AC-N 形式 ID 化"。
- [ ] 主控 TaskResult 字段表新增 `ac_coverage` 字段（array<object>，非必填，元素含 ac_id/covered/evidence）。
- [ ] executing 执行循环新增"填写 ac_coverage" 步骤。

### Task T-008: A4 Scope Drift Detector
**Owner role:** Implementer
**Files:** `skills/task-driver-executing/SKILL.md`
**Acceptance:** AC-6
**Review gate:** checklist 可操作

- [ ] executing 新增段落 "Scope Drift Detector"。
- [ ] 定义触发时机：每个任务的 TaskResult 写入前。
- [ ] 定义比对规则：files_changed 是否子集于 plan File Map（含 Create/Modify/Test 路径）。
- [ ] 不一致时强制停机回问，禁止悄悄扩 scope。
- [ ] 反例门禁追加 "files_changed 超出 File Map 但继续推进" 视为违规。

### Task T-009: A1 Iteration Packet
**Owner role:** Implementer
**Files:** `skills/task-driver-planning/SKILL.md`、`skills/task-driver/SKILL.md`、`skills/task-driver-executing/SKILL.md`、`skills/task-driver-verification/SKILL.md`
**Acceptance:** AC-7
**Review gate:** 字段闭环 + 与 2 轮循环对齐

- [ ] planning Ledger 模板新增段 `## Iteration Log`，列表项格式：`- attempt / requirement_id / hypothesis / command / result / next_assumption / outcome`。
- [ ] 主控执行-验证循环退出段落引用 iteration_log，要求每轮写入。
- [ ] executing 执行-验证循环段落引用同字段。
- [ ] verification 循环退出段落引用同字段。

### Task T-010: A5 Plan-revision 协议
**Owner role:** Implementer
**Files:** `skills/task-driver-planning/SKILL.md`、`skills/task-driver/SKILL.md`
**Acceptance:** AC-8
**Review gate:** 版本号与回流路径明确

- [ ] planning Plan 模板顶部新增 `**Plan version:** v1` 与 `**Predecessor:** [前序 plan 路径或"无"]`。
- [ ] 新增段落 "Plan Revision Protocol"。
- [ ] 明示 plan-revision 触发条件、版本号递增（v1 → v2）、与 spec 关系（spec 不变则只升 plan；spec 变更则回到 brainstorming 写新 spec）。
- [ ] 要求 v2 必须列 `## Diff From v1` 段，简述结构性差异。
- [ ] 主控循环退出段落引用本协议。

### Task T-011: A2 User Acceptance Gate
**Owner role:** Implementer
**Files:** `skills/task-driver-verification/SKILL.md`、`skills/task-driver/SKILL.md`
**Acceptance:** AC-9
**Review gate:** 与"不得每步讨确认"无冲突

- [ ] verification 新增段落 "User Acceptance Gate"。
- [ ] 触发时机：VerificationReport 写完且所有 AC 至少 Met/Partial 后，且仅触发一次。
- [ ] 定义流程：agent 给出交付清单 + 证据摘要 → 用户回复 accept / reject / partial-accept → ledger 记录 `delivery_acknowledged_by_user: true|false|partial`。
- [ ] reject 时回到执行或 plan-revision；partial 时记录残余项。
- [ ] 主控相关段落引用本门。
- [ ] 显式声明：本门不与"已确认 plan 后不得每步讨确认"冲突，因为只在最终触发一次。

### Task T-012: 同步根 SKILL.md + CHANGELOG
**Owner role:** Implementer
**Files:** `SKILL.md`、`CHANGELOG.md`
**Acceptance:** AC-12 + AC-13 + AC-14
**Review gate:** 兼容性 + 现有约束未破坏

- [ ] 根 `SKILL.md` 在"核心契约"和"反例门禁"段补充本次新增条款的精简版（Task ID、AC ID、ac_coverage、Scope Drift、iteration_log、plan-revision、User Acceptance Gate）。
- [ ] CHANGELOG 新增 `## v0.4.3 (2026-06-23)` 段，列出 11 条补丁。
- [ ] 自检：5 阶段、2 轮循环、品质三档、反例门禁清单仍在。

## Verification Plan

- 命令：grep / 阅读关键段（无可执行测试，markdown-only 协议）。
- 逐条对账 14 条 AC，写入 VerificationReport。
- 预期 evidence_strength：每条 AC 至少 strong（直接检查目标产物文本）。

## Stop Conditions

- 任一文件读取失败或路径冲突。
- packet 字段表与现有 YAML 字段语义冲突，需 spec 决策。
- Scope Drift 触发（files_changed 超出本 plan File Map）。
- 同一 task 失败 2 轮仍未通过 → blocked / partial / plan-revision。
