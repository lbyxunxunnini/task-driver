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
- 只完成某个优先级阶段、批次、小目标或子任务，就询问用户是否继续执行已批准计划。
- plan 没有目标达成定义或验证方案摘要，却已经进入执行。
- 没有完成验收前自检，就进入 User Acceptance Gate 询问用户是否接受。
- 跳过 brainstorming / planning / executing / verification / User Acceptance Gate，但没有记录跳过原因、风险、替代证据和用户批准。
- planning 或 executing 发现未澄清的目标、范围、AC、技术方案或风险细节，却继续向下游推进。
- Design Tree Coverage 存在 open 分支，却进入 planning、executing 或 verification。
- 目标写“全部 / 完整 / 100% / 迁移 / 覆盖”，但没有 scope_denominator 或目标覆盖矩阵。
- 实际只完成目标子集，却把最终报告改写成“核心完成”“主要完成”。
- 用文件存在、文本命中、只看 diff 或只读代码冒充功能级完成。
- 自检发现问题后只改文字或重复粗检查，没有复验证明问题类型消除。

## Target-Driven State Machine

每个 Task Driver 任务必须维护目标定义[Target]，并让所有 packet 引用同一目标：

- `target_id`
- `target_statement`
- `success_definition`
- `scope_denominator`
- `target_principles`
- `quality_level`
- `stop_or_loop_conditions`

正常状态链：

```text
Target -> brainstorming -> planning -> executing -> verification -> User Acceptance Gate -> accepted_by_user
```

必经规则：

- brainstorming、planning、executing、verification、User Acceptance Gate 都必须出现。
- executing、verification、User Acceptance Gate 是交付前硬必经环节；除非用户明确取消交付或将任务降级为纯规划/纯审查，否则不得跳过。
- 任何跳过都必须写入 ledger：`skipped_stage / reason / risk / replacement_evidence / user_approval`。
- 没有跳过记录时，后续阶段必须回退补齐，不得继续包装成完成。
- scope_denominator 是目标覆盖分母。PlanPacket 必须为每个目标单元建立 target_coverage_matrix；VerificationReport 必须为每个目标单元建立 target_coverage。
- target_principles 是取舍约束。任何任务顺序、验证强度、延期、降级或 partial 判断都必须能回指目标原则。

回路规则：

- planning 发现 spec 未闭合或技术取舍未确认 -> brainstorming。
- executing 发现依赖未澄清细节、AC 不可验证、方案取舍未确认或风险边界变化 -> brainstorming；若 spec 正确但计划错误 -> planning。
- verification 发现实现缺陷且不改变计划 -> executing；发现计划假设错误 -> planning；发现目标、范围、AC、质量层级或风险边界错误 -> brainstorming。
- verification 发现目标覆盖不足、功能级证据不足或自检循环未闭合 -> executing / planning / brainstorming；不得直接进入 User Acceptance Gate。
- User Acceptance Gate 被 reject -> 根据拒绝原因回到 executing / planning / brainstorming；不得默认只做小修。

## 目标兼容生命周期[Goal Compatibility Lifecycle]

Goal 兼容层把 Target 映射到宿主 agent 的目标模式，但 Task Driver 的 packet 和 ledger 仍是审计单源。

### Provider 选择

- `codex`：当前环境有 `get_goal` / `create_goal` / `update_goal` 工具时使用。
- `claude-code`：当前环境支持 Claude Code `/goal`，但没有 Codex Goal 工具时使用。
- `ledger-only`：目标模式不可用、hook 被禁用、版本不支持或无法从当前 agent 控制时使用。

### 激活规则

- brainstorming 阶段不得激活 Goal。
- planning 阶段必须从 approved SpecPacket 生成 GoalDraft。
- executing 阶段启动前读取 GoalDraft，并按 provider 激活：
  - Codex：先检查现有 goal；没有 active goal 才创建；target_id 冲突必须停机回问。
  - Claude Code：输出 `/goal <condition>` 字符串；因为新 `/goal` 会替换旧 goal，发现已有 active goal 时必须让用户确认，不得自动覆盖。
  - ledger-only：写 `goal_provider: ledger-only` 和降级原因，使用 ledger 的 Target / Iteration Log / VerificationReport 维持目标。

### Claude Code 条件要求

Claude Code 的 evaluator 只看对话中已展示的证据，不独立运行命令或读文件。因此 `/goal` 条件必须要求 agent 在每轮输出或 ledger 中展示：

- 验证命令和结果。
- 每个 AC 的状态。
- 每个 scope_denominator 目标单元的状态。
- 未满足项、下一步假设和阻塞原因。

### 完成规则

- Goal active 不等于任务完成。
- Codex 目标[Codex Goal]不得在 VerificationReport 通过前 `update_goal complete`。
- Claude Code goal 自动 clear 只代表 evaluator 认为条件满足；Task Driver 仍必须写 VerificationReport 并进入 User Acceptance Gate。
- ledger-only 的 GoalDraft.status 只能在 VerificationReport 有强证据覆盖全部目标分母后写 `complete`。
- Goal complete 之前必须运行隔离目标检测[goal_detection]：由独立 subagent / isolated verifier 只读取 SpecPacket、GoalDraft、PlanPacket、ledger evidence、VerificationReport 草稿和必要文件/命令输出，不读取当前执行上下文推理。检测结果写入 VerificationReport.isolated_goal_detection。检测实现可降级为新会话、外部工具或人工隔离审查，但不得降级为同上下文自检；没有任何隔离检测路径时，不得 complete。

## No Silent Downscope

禁止静默降级：

- 目标包含“全部 / 完整 / 100% / 迁移 / 覆盖”时，未覆盖目标单元是阻断问题，不是 minor backlog。
- 任何目标单元被删除、延期、改弱或改成 partial，都必须获得用户明确批准，并写入 Decision Trace、ledger Decisions 和 VerificationReport.unmet_requirements[]。
- 若执行中发现原目标过大或分母错误，必须回到 brainstorming 或 plan-revision；不得在最终报告中重新解释目标。
- Review Gate 发现目标单元遗漏时，必须标 Critical。

## Functional Verification Gate

完成声明必须优先使用功能级证据：

- 新增功能：验证用户可观察行为，而不是只验证代码写入。
- 迁移任务：验证迁移分母中的每个模块、配置、命令、测试或运行路径。
- 协议或 skill 优化：用反例样例、契约检查或 walkthrough 证明新规则能拦住旧问题。
- 文档任务：若目标是纯文字修正，可用文本检查；若目标是流程、门禁或规则生效，必须补语义级或功能级验证。

文件存在、文本命中、diff 审查、只读代码默认是 weak evidence，不能支撑 Met。

## Self-Test Improve Loop

协议修改、packet schema 修改、示例修改或发布前自测必须走自检优化循环：

```text
生成/修改 -> 运行自检 -> 分类发现 -> 修复或回退 -> 复验 -> 记录证据
```

每轮必须写入 ledger 或最终报告：检查项、发现类型、路由、修复动作、复验证据和循环次数。同一问题最多 2 轮；仍失败时必须 blocked、plan-revision 或 brainstorming。

## Whole-Plan Progression

approved plan 是连续执行契约。用户确认 plan 后，agent 必须按 PlanPacket.tasks[] 推进到以下任一终态：

- 所有任务完成并进入 verification。
- Review Gate、Scope Drift、停机条件、blocked、partial、plan-revision 或 brainstorming 回退。
- 用户明确暂停或修改目标。

阶段、优先级批次、小目标和单个任务完成都不是终态。它们只能产生 ledger 更新、TaskResult、ReviewReport 和简短进度更新；不得触发“是否继续”。

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

VerificationReport 写完、所有 AC 至少 Met/Partial、验收前自检无 fail 后，状态进入 `awaiting_user_acceptance`，触发 User Acceptance Gate。用户回复后状态变为 `accepted_by_user` / `rejected_by_user` / `partial`。该门只在最终触发一次，不与“已确认 plan 后不得每步讨确认”冲突。

Partial 仅在同时满足以下条件时可进入 User Acceptance Gate：

- 核心用户路径或核心目标已被 strong 或 medium 证据覆盖。
- 未覆盖部分不涉及安全、权限、数据、迁移、发布、依赖、构建配置、公共 API。
- 未覆盖部分不会造成主要流程不可用或用户可见严重回归。
- VerificationReport.unmet_requirements[] 已列出缺口、原因、next_action。
- 最终报告明确提示用户这是 partial 交付，并请求 accept / reject / partial-accept。

否则 Partial 不得进入 User Acceptance Gate，必须回到 executing、blocked 或 plan-revision。
