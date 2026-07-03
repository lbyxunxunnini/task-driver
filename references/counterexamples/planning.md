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
