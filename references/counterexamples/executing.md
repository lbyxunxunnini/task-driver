# Executing Counterexamples

这些反例命中时，必须停止执行，按 blocked、plan-revision 或 brainstorming 路由处理。

## 未确认 spec/plan 就写代码

- 错误：用户需求较大或跨文件时，直接开始改实现。
- 违规：没有 approved spec 或 approved plan。
- 回退：回到 brainstorming 或 planning，补齐确认状态。

## 静默跳过 plan 步骤

- 错误：某个计划步骤跑不通，就改做另一个看似等价的步骤但不记录。
- 违规：破坏 PlanPacket 单源和验证链。
- 回退：记录失败原因；若不改变 AC/风险可作为替代步骤写入 ledger，否则 plan-revision。

## 范围漂移继续推进

- 错误：为修一个问题顺手改了不在 File Map 的文件，仍继续任务。
- 违规：Scope Drift Detector 未拦截。
- 回退：停机回问是否扩 scope，或进入 plan-revision。

## 盲目循环修复

- 错误：验证失败后连续“再改一下再测一下”，超过两轮没有状态分类。
- 违规：违反执行-验证循环上限。
- 回退：写 Iteration Log，并进入 blocked、partial、plan-revision 或 brainstorming。

## 伪多 agent

- 错误：没有 subagent 工具却声称“已派发 reviewer/verifier agent”。
- 违规：伪造执行证据。
- 回退：使用 single-agent，并记录没有 subagent 能力。

## 无 Review Gate

- 错误：任务小、只是文档或测试改动，所以跳过 ReviewReport。
- 违规：每个 PlanPacket task 都必须执行 Review Gate。
- 回退：按风险调整深度，但必须写 ReviewReport。
