---
name: task-driver-executing
description: "执行阶段。用于 approved plan 之后：按计划连续执行、检查分支/工作区、TDD、可选 subagent 派发、single-agent 降级、写 TaskResult/ReviewReport、更新 ledger。"
---

# 执行阶段

执行 approved plan，不重新发明需求。按任务推进，更新 ledger，边做边验证，只在定义的停机条件下回问。

## 执行前检查

编辑前必须：

1. 读取 approved plan 和 ledger。
2. 检查 git status 和当前分支。
3. 如果在 `main`/`master` 上做非小型修改，先询问或使用隔离分支/工作区。
4. 运行 plan 指定的 baseline verification（如果有）。
5. 检查 plan 是否有矛盾、缺失依赖或不可执行步骤。
6. 确认执行模式。没有明确 subagent 工具时，使用 `single-agent`。

## 多 Agent 降级

不得要求环境必须支持 subagent。

### 没有 subagent 时

使用 `single-agent`：

- 当前 agent 自己执行每个任务。
- 执行前读取 ledger 中的 PlanPacket。
- 执行后写 TaskResult。
- 另起一遍思路做 Review Gate，并写 ReviewReport。
- 最后交给 verification 阶段写 VerificationReport。

### 有 subagent 时

可以使用 `multi-agent-review` 或 `multi-agent-parallel`：

- 只把相关 packet 和必要文件路径交给 subagent。
- 要求 subagent 返回 TaskResult 或 ReviewReport。
- 不接受纯散文总结作为完成证据。
- controller 保留最终责任；subagent 输出只是证据，不是权威。

## 执行循环

每个任务：

1. 在 ledger 标记 `in_progress`。
2. 按 plan 步骤执行；除非步骤不可能或不安全。
3. 行为变化走 TDD：
   - 先写失败测试。
   - 运行并确认失败原因符合预期。
   - 做最小实现。
   - 运行测试和相关回归检查。
   - 只在测试保持通过时重构。
4. 只有用户或 plan 要求 commit，且任务已验证，才 commit。
5. 更新 ledger：改动文件、命令、结果、commit、风险。
6. 写 TaskResult packet。
7. 做 Review Gate。
8. 写 ReviewReport packet。

## 执行-验证循环退出

同一 requirement 最多执行-验证 2 轮。每轮都要在 ledger 记录尝试内容、验证命令、结果、失败原因和下一步假设。

第 2 轮后仍未通过时，停止继续修补，并写入：

- `blocked`：需要用户决策、权限、环境、外部服务或范围调整。
- `partial`：核心目标满足但存在明确缺口，等待用户接受或拒绝。
- `plan-revision`：原 plan 假设错误，必须回到计划阶段。

不得无限重复“修一下再测一下”。

## 执行反例

这些情况必须停止或回退：

- 跳过失败测试，直接实现行为变化。
- 实现时发现需要新接口或新模块，但 plan 没有定义，仍继续扩 scope。
- 任务没写 TaskResult，就进入下一个任务。
- review 发现 Critical/Important，但只记录不修复。
- subagent 没返回结构化 packet，却把它的散文总结当作通过。
- 同一 requirement 已失败 2 轮，仍继续盲修。

## 阶段输出：TaskResult

字段以 `skills/task-driver/SKILL.md` 的结构化交接 Packet 为准；本阶段至少写入 task id、状态、修改文件、运行命令、证据、偏离 plan 的地方、未关闭风险。

## Review Gate

每个有意义任务都检查：

- Spec compliance：任务验收是否满足，是否遗漏要求，是否加入未授权行为。
- Code/content quality：改动是否足够小、命名清楚、符合本地模式、无无关重构、无脆弱测试、无隐藏 TODO。
- Verification：命令输出是否新鲜，是否覆盖该任务。

Critical 或 Important 问题阻塞继续。必须修复并复审后进入下一个任务。Minor 可以进入 ledger backlog。

## 阶段输出：ReviewReport

字段以 `skills/task-driver/SKILL.md` 的结构化交接 Packet 为准；本阶段至少写入 task id、状态、findings、severity、file、issue、required fix。

## 停机条件

出现以下情况停下问用户：

- plan 指令不清楚或不可执行。
- 测试反复失败且根因未知。
- 修复需要扩大 scope。
- plan 要求和代码质量或安全冲突。
- 任务需要未明确批准的破坏性 git/文件操作。
- 依赖、凭据、环境或外部服务阻塞，且无安全替代路径。

不要为了总结进度而停。给简短进度更新，然后继续执行。

## 恢复规则

上下文压缩或会话恢复时：

1. 先读 ledger。
2. 相信 ledger 和 git history，优先于记忆。
3. 从第一个未完成任务恢复。
4. 继续前检查工作区状态。

## 完成移交

所有 plan 任务完成后，进入 `task-driver-verification`。验证前不得宣称完成。
