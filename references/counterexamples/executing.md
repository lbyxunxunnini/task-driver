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

## 小目标完成后询问是否继续

- 错误：完成 P0、某个批次或前几个任务后，展示进度表并问“下一步进入 P1，是否继续？”
- 违规：approved plan 已经授权连续执行整个 PlanPacket；阶段性完成不是停机条件。
- 回退：把进度写入 ledger，继续执行下一个 pending task；若全部任务完成，则立即进入 verification。

## 30% 冒充 100%

- 错误：目标是完整迁移 10 个模块，实际只迁移 3 个模块，最终写“核心模块已完成，整体可交付”。
- 违规：scope_denominator 中未覆盖目标单元是阻断问题，不能改写成核心完成。
- 回退：停止完成声明；补齐剩余目标单元，或进入 plan-revision / blocked / brainstorming 请求用户明确降级。

## 未覆盖项进普通 backlog

- 错误：目标范围内某个 AC 或目标单元未做完，ReviewReport 标 minor 放入 backlog。
- 违规：目标范围内未覆盖项影响完成真实性，必须 Critical 或 Important。
- 回退：升级 finding；修复、blocked、plan-revision，或由用户明确批准 partial。

## 执行中弱化验证

- 错误：plan 要求运行样例或测试，执行阶段改成“检查文件已写入”并继续下个任务。
- 违规：验证强度下降会改变 AC 状态和目标可信度，不能由执行阶段自行降级。
- 回退：运行原功能级验证；无法运行时记录原因和证据强度上限，按 blocked / partial / plan-revision 路由。

## 边做边改目标

- 错误：发现目标过大后，执行阶段直接缩小 scope 或删除目标单元，没有回到 brainstorming。
- 违规：目标、范围分母和目标原则属于 spec 契约，不得执行中静默改写。
- 回退：停止当前任务，回到 brainstorming 或 plan-revision，并等待用户确认。
