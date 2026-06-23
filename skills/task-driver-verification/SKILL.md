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
- 运行 plan 的验证命令，或说明为什么无法运行。
- 测试类证据：报告命令、退出码、pass/fail 数量或关键输出。
- 非代码工件：检查能证明要求的文件或渲染结果。
- Review gate：确认 Critical/Important findings 已修复或被用户明确 deferred。
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
   - `reject`：ledger 写 `delivery_acknowledged_by_user: false`，附拒绝原因；根据原因回到执行阶段或踏入 plan-revision。
   - `partial-accept`：ledger 写 `delivery_acknowledged_by_user: partial`，记录接受项与残余项；残余项进入 backlog 或 plan-revision。
4. 未获 accept 前，不得宣称交付完成。

与“已确认 plan 后不得每步讨确认”不冲突：本门仅在最终验证后触发一次，不是中段询问。

## 循环退出

验证失败后可以回到执行阶段，但同一 requirement 最多 2 轮。每轮必须在 ledger 的 `## Iteration Log` 段写入完整记录（attempt / requirement_id / hypothesis / command / result / next_assumption / outcome）。第 2 轮仍失败时，必须输出 `blocked`、`partial` 或 `plan-revision`，不得继续要求执行阶段盲修。

## 失败处理

验证失败时：

- 写明失败命令或证据。
- 写明哪条 requirement 未满足。
- 回到执行或调试。
- 不得在验证失败时提出 merge、PR、cleanup，除非用户明确接受已知失败。

## 最终报告

包含：

- 改动摘要。
- spec、plan、ledger 路径。
- 验证证据。
- 验收标准状态。
- 残余风险和 deferred items。
- 是否已满足用户选择的交付路径。
