# Planning Counterexamples

这些反例命中时，必须停在 planning 阶段或回到 brainstorming，不得进入 executing。

## 占位式任务

- 错误：plan 写“完善逻辑”“适当处理异常”“补充测试”。
- 违规：任务不可执行，无法交给新 agent 复现。
- 回退：每个任务必须写文件、步骤、验收项、验证命令和预期结果。

## 缺少 File Map

- 错误：计划只写改哪些功能，不列允许修改的文件集合。
- 违规：executing 无法执行 Scope Drift Detector。
- 回退：补齐 File Map；无法确定时继续事实收集或回到 brainstorming。

## 验证命令不可执行

- 错误：写“运行测试确认通过”，但没有具体命令、目录、预期输出或替代检查。
- 违规：verification 无法获得 fresh evidence。
- 回退：写出可运行命令；不能运行时记录原因、替代证据和证据强度上限。

## assumption 无验证点

- 错误：写“假设现有 API 可复用”，但没有依据、验证任务或失效处理。
- 违规：assumption 不可检验，执行阶段会盲修。
- 回退：为每个 assumption 写 `ASM-N`、依据、验证点、失效处理和影响范围。

## spec 缺口被 plan 吞掉

- 错误：发现 Goal、AC、Scope 或 Quality level 不清楚，却在 plan 中自行补默认值。
- 违规：plan 改写了 spec。
- 回退：回到 brainstorming 补 spec，并重新获得用户确认。

## 只有任务清单没有目标和验证方案

- 错误：plan 只列 T-001、T-002、T-003，没有 `Goal`、`Success Definition` 和 `Verification Strategy`。
- 违规：执行者只能推进小任务，无法判断整体目标是否完成，也无法在 verification 阶段逐条证明。
- 回退：补齐目标达成定义和验证方案摘要，确保每条 AC 映射到任务或最终验证命令。

## 把技术方案决策伪装成执行任务

- 错误：plan 写“实现方案 A / 方案 B 之一”，或在用户未确认取舍轴时直接选一个方案开工。
- 违规：会改变接口、依赖、验证方式、风险边界或交付范围的方案选择必须在 brainstorming 闭合。
- 回退：回到 brainstorming，用单问题澄清门让用户确认方案轴或方案选择；确认后重写 plan。

## 没有 Decision Trace 就写计划

- 错误：spec 只有 Goal、Scope 和 AC，plan 直接拆 T-001/T-002，没有记录宏观到细节的用户决策链。
- 违规：无法证明计划里的范围切片、技术方案和验证策略已经与用户达成一致。
- 回退：回到 brainstorming 补 Decision Trace；至少闭合整体目标、大类/规划轴、范围切片、行为细节和实现约束中会影响本轮交付的层级。

## shared_understanding 未成立就写计划

- 错误：Grilling Summary 中 `shared_understanding: false` 或未记录，仍开始写 plan。
- 违规：plan 必须建立在共同理解上；否则任务拆解会替用户隐性做决策。
- 回退：回到 brainstorming 输出共享理解摘要，并等待用户明确确认。

## 设计树仍有 open 分支

- 错误：Design Tree Coverage 中验证策略或风险分支仍是 open，plan 已经开始拆任务。
- 违规：open 分支代表仍有会影响 AC、风险或验证的未决问题；planning 不能替用户默认。
- 回退：回到 brainstorming 关闭 open 分支，或明确 deferred / out_of_scope 并说明影响。

## Phase 包装成任务

- 错误：plan 写 `Phase 1：补齐目标治理`、`Phase 2：优化流程`，每个 Phase 只有文件列表和一句成功外观。
- 违规：Phase 是组织层级，不是可执行任务；执行者无法知道具体行为、AC、验证和停机条件。
- 回退：拆到 Task T-NNN，每个任务包含目标单元、文件、行为/内容变化、AC 引用、功能级验证和 Review Gate。

## 产物名替代设计决策

- 错误：`为 stage2 建立 cover-quality-rubric.md`，但没有说明 Rubric 的评价对象、维度、评分尺度、阈值、证据来源和失败反例。
- 违规：文件名不是设计决策，评价模型会改变验收口径，必须在 brainstorming 闭合。
- 回退：回到 brainstorming 确认评价模型；确认后再写计划任务。

## 缺少目标覆盖矩阵

- 错误：目标是“全部整改”，plan 只列任务，没有把 scope_denominator 的每个目标单元映射到 T-NNN 和验证项。
- 违规：无法防止 100% 目标实际只做 30%。
- 回退：补 Target Coverage Matrix；任何未覆盖目标单元都是 Critical 缺口。

## 只有文件列表没有子问题拆解

- 错误：plan 写“修改各阶段 SKILL.md”，但没有说明每个阶段要解决的问题、行为变化和验证方式。
- 违规：文件列表不能证明拆解深度，也不能指导执行和评审。
- 回退：按拆解轴继续拆成可验证任务；若子问题会影响目标、AC 或验证，回到 brainstorming。
