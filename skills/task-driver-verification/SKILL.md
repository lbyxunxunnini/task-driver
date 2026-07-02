---
name: task-driver-verification
description: "验证阶段。用于声明完成、修好、通过、ready、可交付之前：读取 spec/plan/ledger，检查 TaskResult/ReviewReport，运行 fresh verification，对验收标准逐条给证据。"
---

# 验证阶段

先证据，后声明。没有本轮新鲜证据，不得说完成、修好、通过、ready 或可交付。

## 验证门禁

作出任何成功声明前：

1. 明确要声明什么。
2. 找到能证明该声明的命令、文件、渲染结果、diff、日志或运行行为。
3. 获取 fresh evidence。
4. 对照 approved spec 的每条验收标准和 plan 的每条验证项。
5. 检查 ledger 中的 TaskResult 和 ReviewReport。
6. 更新 ledger。
7. 只汇报证据支持的结论。

## 证据强度

每条 requirement 的证据必须标注：

- `strong`：新鲜运行结果或直接检查目标产物，覆盖对应验收标准。
- `medium`：覆盖核心路径但缺少部分边界；只能标 `Partial` 并写 caveat。
- `weak`：只看 diff、只读代码、只跑窄检查或证据间接；不能支撑完成声明。
- `stale`：旧会话、旧日志、旧测试结果；不能支撑完成声明。

状态规则：

- `strong` → 可标 `Met`。
- `medium` → 最多标 `Partial`。
- `weak` / `stale` → `Not met` 或 `Blocked`。

## 必查项

- 读取 approved spec。
- 读取 approved plan。
- 读取 ledger。
- 检查 git diff/status。
- 必须运行 plan 的验证命令。
- 只有在命令确实无法运行时，才允许跳过；跳过必须写入 VerificationReport.unmet_requirements[] 或 ledger Evidence，并包含：
  - 无法运行的具体命令。
  - 失败/跳过原因分类：环境缺失 / 权限缺失 / 依赖缺失 / 外部服务不可用 / 命令不存在 / 风险过高。
  - 已尝试的修复或诊断命令。
  - 替代验证方式及其 evidence_strength。
  - 对 AC 状态的影响。
- 未运行原验证命令时，不得将对应 AC 标为 `Met`；最多为 `Partial`，且必须满足 Partial 进入 User Acceptance Gate 的条件。
- 若无替代验证，必须标为 `Blocked`，不得宣称完成。
- 测试类证据：报告命令、退出码、pass/fail 数量或关键输出。
- 非代码工件：检查能证明要求的文件或渲染结果。
- Review gate：确认 Critical/Important findings 已修复。只有满足以下条件，Important 才可被用户明确 deferred：
  - 不影响任何 AC 的 Met 判定。
  - 不涉及安全、权限、数据、迁移、发布、依赖、构建配置、公共 API。
  - 不造成用户可见严重回归或主要流程不可用。
  - VerificationReport.unmet_requirements[] 记录 deferred 原因、owner、next_action。
- Critical finding 不得 deferred；必须修复、blocked 或 plan-revision。
- 被 deferred 的 Important finding 会将相关 AC 最高限制为 Partial，不得标 Met。
- 多 agent 任务：检查结构化 TaskResult 和 ReviewReport。
- single-agent 降级任务：只有包含具体证据的 packet 才能接受。

## 完成审计表

最终报告必须包含：

```markdown
| AC ID | Requirement | Evidence | Strength | Status |
|---|---|---|---|---|
| AC-1 | [验收标准] | `[命令/文件]` -> [结果] | strong/medium/weak/stale | Met / Partial / Not met / Blocked |
```

AC ID 必须引用 SpecPacket.acceptance_criteria[].id，不得生造或重命名。证据弱、过期、间接或缺失时，状态必须是 `Not met`。不得把不确定包装成完成。

## 验证反例

这些不能作为完成证据：

- “代码已经改了，看起来没问题。”
- “测试应该会过”，但没有命令输出。
- 只运行了一个窄测试，却声称整个功能完成。
- 使用上一次会话的旧测试结果。
- 验证没有覆盖 spec 的某条 acceptance criterion。

## 阶段输出：VerificationReport

写入 ledger。字段以 `skills/task-driver/SKILL.md` 的结构化交接 Packet 为准；本阶段至少写入：

- `status`（met / partial / not_met / blocked / awaiting_user_acceptance / accepted_by_user）。
- `mode`（与 plan 一致）。
- `coverage[]`：每项 `{ac_id, evidence_ref, evidence_strength, status}`；ac_id 引用 SpecPacket。
- `unmet_requirements[]`：每项 `{ac_id, reason, next_action}`。
- `delivery_acknowledged_by_user`：初值 `pending`；进入 User Acceptance Gate 后按用户回复更新为 `true / false / partial`。

## User Acceptance Gate

触发时机：VerificationReport 写毕且所有 AC 状态至少 Met/Partial 后，仅触发一次。

流程：

1. 状态进入 `awaiting_user_acceptance`。
2. agent 向用户输出交付清单 + 证据摘要：改动文件列表、spec/plan/ledger 路径、完成审计表、残余风险、已知缺口。
3. 用户回复三选一：
   - `accept`：状态 → `accepted_by_user`，ledger 写 `delivery_acknowledged_by_user: true`，任务收尾。
   - `reject`：状态 → `rejected_by_user`，ledger 写 `delivery_acknowledged_by_user: false`，附拒绝原因；根据原因回到 executing、blocked、plan-revision 或 brainstorming。
   - `partial-accept`：ledger 写 `delivery_acknowledged_by_user: partial`，记录接受项与残余项。
4. 未获 accept 前，不得宣称交付完成。

残余项只有同时满足以下条件，才可进入 backlog：

- 用户明确接受当前 partial 交付。
- 残余项不影响已接受 AC 的真实性。
- 残余项不涉及安全、权限、数据、迁移、发布、依赖、构建配置、公共 API。
- 残余项不会造成主要流程不可用或用户可见严重回归。
- backlog 条目包含 owner、原因、建议处理方式和后续触发条件。

不满足任一条件时，残余项必须进入 plan-revision 或 blocked，不得进入普通 backlog。

与“已确认 plan 后不得每步讨确认”不冲突：本门仅在最终验证后触发一次，不是中段询问。

## 循环退出

验证失败后不得默认回执行阶段，必须先分类：

- 回到 executing：失败原因定位明确，修复不改变 spec、plan、AC、文件映射、风险边界，且仍在 2 轮上限内。
- blocked：失败原因依赖用户决策、权限、环境、外部服务、凭据、不可替代验证，或根因未知。
- partial：核心目标已有足够证据，缺口满足 Partial 进入 User Acceptance Gate 的条件。
- plan-revision：失败暴露 plan 假设错误、任务顺序错误、文件映射错误、接口/依赖假设错误、验证命令设计错误。
- brainstorming：失败暴露 goal、scope、AC、constraints、quality level 或风险边界错误。

每次分类必须写入 Iteration Log 的 `next_assumption` 和 `outcome`。同一 requirement 最多 2 轮；第 2 轮仍失败时，必须输出 `blocked`、`partial`、`plan-revision` 或回到 `brainstorming`，不得继续要求执行阶段盲修。

## 失败处理

验证失败时：

- 写明失败命令或证据。
- 写明哪条 requirement 未满足。
- 按“循环退出”中的失败分类选择下一状态：executing / blocked / partial / plan-revision / brainstorming。
- 若选择 executing，必须写明明确根因、下一轮假设、目标文件/任务和验证命令。
- 不得使用“调试”作为状态；调试动作必须归入 executing，并受 2 轮上限约束。
- 不得在验证失败时提出 merge、PR、cleanup，除非用户明确接受已知失败。

## 最终报告

包含：

- 改动摘要。
- spec、plan、ledger 路径。
- 验证证据。
- 验收标准状态。
- 残余风险和 deferred items。
- 用户验收状态：`delivery_acknowledged_by_user` = pending / true / false / partial。
- 交付路径判定：
  - `accepted_by_user`：用户已明确 accept。
  - `awaiting_user_acceptance`：验证完成但等待用户验收；不得宣称交付完成。
  - `partial`：用户 partial-accept 或存在未关闭残余项；必须列出 accepted items、residual items 和路由。
  - `rejected_by_user / blocked`：用户 reject 或关键 AC 阻塞；必须列出回退阶段和 next_action。
