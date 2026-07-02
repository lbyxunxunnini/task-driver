---
slug: task-driver-user-88546431
displayName: Task Driver
version: 0.4.6
summary: 重任务驱动框架，按事实收集、spec、plan、ledger、执行、评审、验证推进复杂任务。
tags: [agent, workflow, task-management]
license: MIT
name: task-driver-standalone
description: "Task Driver 单 skill 兼容入口。触发关键词：tdr-、task-driver。用于不走插件入口的环境：按事实收集、spec、plan、ledger、执行、评审、验证推进重任务；完整协议在 skills/task-driver/SKILL.md。"
---

# Task Driver 单 Skill 入口

这是根目录兼容入口，用于不走 `.codex-plugin/plugin.json` 的安装方式。

本项目完整控制器在 `skills/task-driver/SKILL.md`。执行复杂任务时，必须优先读取该文件及相关阶段 skill 获取完整 packet、多 agent、阶段交接规则。

如果运行环境只加载根 `SKILL.md` 且不能读取 `skills/` 下的完整协议，只能执行本文最小协议，不得声称已执行完整 Task Driver；同时必须视为 `mode: degraded-single-skill`：

- 记录不可用阶段和降级原因。
- 仍按 Brainstormer、Planner、Implementer、Reviewer、Verifier 顺序执行。
- 补齐 SpecPacket、PlanPacket、TaskResult、ReviewReport、VerificationReport。
- 将阶段结果结构化写入 ledger。
- 最终报告披露降级阶段和是否影响验证证据强度。
- 最终报告明确写明“standalone minimal protocol used”，并说明哪些完整协议规则无法确认。

## 核心契约

1. 事实先行：能从文件、代码、日志、git、文档查到的，不问用户。
2. 先澄清：先闭合 Why、范围、成功标准、质量层级，再谈实现。
3. 单问题澄清：禁止问卷式连续提 1 个以上问题；每轮只问当前最高影响的一个用户决策点，并给 2-3 个互斥选项和推荐答案；能给参考答案时不得借口不能给而退回开放式提问。
4. 写工件：大任务必须写 spec、plan、ledger；spec 中 AC 必须 ID 化 (`AC-N`)，plan 中任务必须 ID 化 (`T-NNN`)。
5. 一次确认：spec 和 plan 确认后，执行阶段不得反复问“是否继续”。
6. TDD 优先：功能、bugfix、行为变化必须先写失败测试；只有用户明确豁免、纯非行为变更、无可运行测试框架且无法安全补充，或目标只能人工/外部系统验收时才可跳过，并必须记录替代验证和证据强度上限。
7. 验证收尾：没有 fresh verification evidence，不得说完成、通过、修好、可交付。
8. 循环退出：同一 requirement 最多执行-验证 2 轮；每轮在 ledger 的 `## Iteration Log` 写入 `attempt / requirement_id / hypothesis / command / result / next_assumption / outcome`；仍失败则进入 blocked、partial 或 plan-revision。
9. 增量覆盖：TaskResult.ac_coverage[] 逐项引用 spec 的 AC 以证明本任务对目标的推进。
10. 范围锁定：executing 阶段每个任务结束前运行 Scope Drift Detector；`files_changed` 超出 PlanPacket File Map 必须停机回问。
11. 计划修订：plan-revision 必须递增 `plan_version`、写 `## Diff From v[N-1]`、前版置 `superseded`，并取得用户重新 approve。
12. 交付验收：验证后状态进入 `awaiting_user_acceptance`，触发 User Acceptance Gate；未获 accept 不得宣称交付完成。

## 反例门禁

遇到这些做法必须回退：

- 没有 approved spec 就开始多文件实现。
- plan 写“补充测试、完善逻辑、适当处理异常”，但没有文件、命令、预期结果。
- spec 中 AC 未 ID 化；plan 中任务未以 `T-NNN` 命名。
- 一次回复里连续列多个澄清问题，或只问开放问题不给选项和推荐。
- 对 User scenario / Risks / Trade-offs / Alternatives 未做影响判断就标 `N/A`。
- 用户确认 plan 后，每完成一个小步骤都问“是否继续”。
- 没有运行验证命令，只根据改动内容说“应该好了”。
- 没有 subagent 工具，却声称“已派发 reviewer agent”。
- 发现 scope 扩大（`files_changed` 超出 File Map），但继续实现新增需求。
- TaskResult 缺失 `ac_coverage` 但 plan 要求增量覆盖。
- 同一 requirement 失败 2 轮后仍继续盲修；或不在 `## Iteration Log` 记录。
- 验证后跳过 User Acceptance Gate 直接宣称交付完成。

## 工件路径

- Spec：`docs/task-driver/specs/YYYY-MM-DD--slug.md`
- Plan：`docs/task-driver/plans/YYYY-MM-DD--slug.md`
- Ledger：`docs/task-driver/ledgers/YYYY-MM-DD--slug.md`

## 最小流程

1. **事实收集**：检查项目结构、README、配置、测试命令、git 状态、日志、现有实现。
2. **澄清与 spec**：禁止问卷式提问；每轮只问一个关键决策，按宏观到细节确认目标、范围、非目标、验收、约束、风险。
3. **计划确认**：写 plan，包含文件映射、接口、任务、测试命令、验证方式、停机条件。
4. **连续执行**：按 plan 执行；行为变化走 TDD；每个任务更新 ledger。
5. **评审**：检查 spec compliance、代码/内容质量、未授权扩张、验证证据。
6. **最终验证**：读取 spec/plan/ledger，运行验证命令，逐条验收。

## Packet 和多 Agent

根入口不重复完整 schema。需要 packet 字段、多 agent 模式或子阶段职责时，读取：

- `skills/task-driver/SKILL.md`
- `skills/task-driver-brainstorming/SKILL.md`
- `skills/task-driver-planning/SKILL.md`
- `skills/task-driver-executing/SKILL.md`
- `skills/task-driver-verification/SKILL.md`

若环境不支持 subagent，默认单 agent 顺序扮演 Brainstormer、Planner、Implementer、Reviewer、Verifier，并把阶段结果结构化写入 ledger；涉及高风险或跨模块任务时，必须在 plan/ledger 记录无法使用 multi-agent-review 的降级原因。

## 停机条件

只在这些情况回问：

- 计划外关键分叉会改变结果。
- 用户原要求冲突或不可实现。
- 影响范围超出已确认边界。
- 验收标准不足以判断完成。
- 工具、环境、权限阻塞且没有安全替代路径。
- 继续会删除、覆盖、发布、合并或丢弃工作。

## 最终报告

必须包含：改动摘要、工件路径、验证命令和结果、每条验收标准的证据、残余风险。
