# Runtime Protocols

## Red Flags

出现这些信号时，必须回退到执行或验证，不得继续包装成完成：

- “应该好了”“看起来没问题”“理论上会过”。
- 只看 diff，没有运行命令或检查产物。
- 只运行窄测试，却宣称整体完成。
- 使用旧测试结果或旧日志。
- 验证没有覆盖某条 acceptance criterion。
- 跳过失败测试直接实现行为变化。
- 反复修同一 requirement 但不记录尝试和退出条件。

## TDD Exceptions

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

## Execution-Verification Loop Exit

同一 requirement 的执行-验证循环最多 2 轮。每轮必须在 ledger 的 `## Iteration Log` 段写入一条记录，字段：`attempt / requirement_id / hypothesis / command / result / next_assumption / outcome`。

第 2 轮后仍失败时，必须停止循环并进入以下之一：

- `blocked`：需要用户决策、权限、环境、外部服务或范围调整。
- `partial`：核心目标满足但存在用户可接受的明确缺口。
- `plan-revision`：原 plan 假设错误，需要回到 plan 阶段，按 Plan Revision Protocol 升级 plan_version。

不得无限“修一下再测一下”。如果根因未知，状态必须是 `blocked` 或 `plan-revision`。

## Plan Revision Protocol

触发条件：执行-验证循环 2 轮仍失败、或执行中发现 plan 假设错误（接口、依赖、范围）。

- spec 仍正确：只升级 plan，`plan_version` 递增（v1 -> v2），`predecessor` 指向前一版 plan 路径，新 plan 顶部新增 `## Diff From v[N-1]` 段简述结构性差异；前一版状态置 `superseded`。
- spec 也错误：必须回到 brainstorming 写新 spec，旧 spec 状态置 `superseded`，再产出新 plan v1。
- plan-revision 必须取得用户对新 plan 的 approve；不得在用户未确认前继续执行。

## User Acceptance Gate

VerificationReport 写完且所有 AC 至少 Met/Partial 后，状态进入 `awaiting_user_acceptance`，触发 User Acceptance Gate。用户回复后状态变为 `accepted_by_user` / `rejected_by_user` / `partial`。该门只在最终触发一次，不与“已确认 plan 后不得每步讨确认”冲突。

Partial 仅在同时满足以下条件时可进入 User Acceptance Gate：

- 核心用户路径或核心目标已被 strong 或 medium 证据覆盖。
- 未覆盖部分不涉及安全、权限、数据、迁移、发布、依赖、构建配置、公共 API。
- 未覆盖部分不会造成主要流程不可用或用户可见严重回归。
- VerificationReport.unmet_requirements[] 已列出缺口、原因、next_action。
- 最终报告明确提示用户这是 partial 交付，并请求 accept / reject / partial-accept。

否则 Partial 不得进入 User Acceptance Gate，必须回到 executing、blocked 或 plan-revision。
