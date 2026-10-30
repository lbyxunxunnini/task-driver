# 轻量状态检查

主控在对话或[唯一任务摘要](state-recovery.md#何时建立记录)中维护原目标、当前环节、已决定事项及来源、未决事项、下一动作和授权。普通讨论在上下文维护状态；达到[记录条件](state-recovery.md#何时建立记录)后，建立或复用同一任务摘要并增量维护问题和回答。不要为了检查重新询问已确定的事项或制造新问题。

需要检查结构或阶段条件时，可以调用 `scripts/workflow_control.py`；脚本只读标准输入或指定的 JSON 状态，不创建、覆盖或更新任务记录。例如 `python3 -B "<skill目录>/scripts/workflow_control.py" next --state -` 从标准输入读取；`check` 只检查结构。脚本未运行或失败不等于检查通过；不可用时说明限制，并按主控协议继续。

状态包含 `task_id`、`phase`、`status`、`next_action`、`decisions`、`plan`、`coverage_checked`、`plan_requested` 和 `gates`。决定项记录稳定 `id`、主题 `subject`、`status`、实际决定 `value` 和 `source`；待定项不需要 `value`。计划的 `presented` 和 `evidence` 来自对话中实际可见的内容，不由脚本自行判断消息是否送达；计划请求和授权分别保留来源。用户只回答一部分时，只更新实际覆盖的决定。填写状态前先查对话和材料，无法恢复的事实标为未知，不猜测。

以下是结构示意，必须按实际对话填写，不把示例当作已有决定：

```json
{"task_id":"当前任务","phase":"analysis","status":"continue","next_action":"分析当前请求","decisions":[],"plan":{"presented":false},"coverage_checked":false,"plan_requested":false,"gates":{"plan":null,"goals":null,"execution":null}}
```

如果有正在运行或结果未知的操作，可用 `operations` 保存其 `id`、实际 `reference`、`status`、`side_effect` 和 `blocks_next`。同一操作不应换标识重复记录；不阻止下一步不自动等于可以宣告整项完成。

脚本返回下一动作供主控参考：仍有影响方案的待决项时调查或讨论；用户要求计划且讨论闭合时列出计划，未闭合时可给标明缺口的草案；没有计划请求时按主控请求结束讨论。计划已展示且用户确认后按主控进入目标环节；旧草案的待核实状态不能挡住已确认的正式计划。计划展示不是确认或执行授权。用户暂停或明确限制本轮范围时优先遵从；未知副作用先核实原操作，不盲目重试。

有上一状态且涉及计划请求撤回、暂停恢复或决定变化时，可以传入 `{"previous":上一状态,"state":当前状态}` 检查明确变化，输出 `scope: structure_and_changes`；未提供上一状态时无法检查跨轮变化。若本次计划已在上一状态交付而本轮才清除请求，记录 `plan_request_delivery_source` 指向本次实际交付；旧计划不能冒充新请求的交付。脚本输出的 `scope: structure_only` 表示只检查结构；它不验证来源的真实性、决定是否被正确理解、问题覆盖是否完整或消息是否实际送达，也不能强迫模型调用。不可访问消息记录文件不妨碍通过可用对话判断下一步；证据不可核实就保留未知，不把普通文件冒充宿主回执。原有摘要的写入、并发和恢复仍由[记录模块](state-recovery.md)处理，本检查器不替换摘要文件。
