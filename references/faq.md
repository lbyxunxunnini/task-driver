# FAQ

从 counterexamples 和实际使用中提炼的常见问题。

## 触发与适用

### Q: 什么时候必须用 Task Driver？
满足任一条件：跨 2 个以上文件或模块；目标、范围、验收不清楚；涉及数据、权限、安全、发布、迁移、外部服务或破坏性操作；需要多步计划或跨阶段验证。详见 `SKILL.md` 的"适用判定"。

### Q: 小任务也要走完整流程吗？
不需要。同时满足以下条件可走小任务豁免：一轮内完成、最多改一个非关键文件、不增删移文件、不涉及高风险改动、无明显方案分叉、有明确验证方式。此时 spec/plan 可内联，不创建独立文件。

### Q: 什么情况下不该用 Task Driver？
- 单文件小修改，结果确定
- 纯问答、纯解释、纯代码阅读
- 一次性数据查询
- 已经有明确 spec 和 plan 的任务（除非需要重新规划）

## 澄清与 Spec

### Q: 澄清时能一次问多个问题吗？
不能。单问题澄清门禁要求每轮只问一个决策点。如果多个信息都缺，先通过本地事实收集缩小不确定性，对低风险细节使用 assumption（标注依据），剩下的最高影响问题才向用户确认。

### Q: 用户说"随便""你决定"怎么处理？
不能用"随便"替代必填门禁（Goal、Scope、Non-goals、AC、Constraints、Quality Level）。对于非必填项，可以标注 assumption 并写明依据；对于必填项，必须指出为什么需要用户决策，给 2-3 个选项和推荐。

### Q: Spec 写到什么程度算"闭合"？
必填门禁全部填写且无占位（TBD、TODO、later），AC 可验证（有具体命令或检查方式），Scope 和 Non-goals 边界清晰不重叠。反例：用"先按常规做""后续再补""大概即可"替代必填项。

## 执行与中断

### Q: 执行到一半被中断了怎么办？
重新触发 task-driver 后，agent 会读取 ledger 末尾的 `## Resume Checkpoint`，检查 git SHA 和文件状态是否一致。一致则从 `next_task` 继续；不一致则从 T-001 重新开始。详见 `references/resume-protocol.md`。

### Q: 验证失败后能无限重试吗？
不能。同一 requirement 的执行-验证循环最多 2 轮。第 2 轮后仍失败，必须进入 blocked / partial / plan-revision，不得继续"修一下再测一下"。

### Q: 执行中发现需要改 plan 里没写的文件怎么办？
触发 Scope Drift Detector。Agent 会停下来展示允许文件集和实际改动，让你决定是否扩展 scope。未经批准不得继续。

### Q: 什么时候可以跳过 Review Gate？
永远不能跳过。但可按风险调整深度：低风险任务走 quick-review（只看 Critical 项），中高风险走 full-review。Review Gate 是强制门禁，不是可选项。

## 多 Agent

### Q: 没有 subagent 工具能用 Task Driver 吗？
能。Task Driver 默认模式就是 single-agent，同一个 agent 按 Brainstormer → Planner → Implementer → Reviewer → Verifier 顺序执行。没有 subagent 时自动降级，不阻塞任务。

### Q: 多 agent 的 review 结果能直接当结论吗？
不能。子 agent 输出只是证据，controller 保留最终判断权。必须对照 spec/plan/ledger 做最终验证。

## 质量与验收

### Q: 质量评分低于阈值怎么办？
按 improve loop：选出最低 1-2 个维度 → 写明缺口 → 还在 scope 和 2 轮上限内就回 executing → plan/spec 有问题就 plan-revision 或 brainstorming → 依赖外部决策就 blocked。不得为提高评分扩大 scope。

### Q: Partial 交付可以验收吗？
可以，但必须满足严格条件：核心路径有 strong/medium 证据覆盖，未覆盖部分不涉及安全/权限/数据/发布，有明确的缺口清单和 next_action，最终报告明确告知用户这是 partial 交付。

### Q: 验收时需要用户做什么？
User Acceptance Gate 触发时，Agent 会展示完成审计表（所有 AC 的状态和证据）、质量评分（如适用）和残余风险。用户回复 accept / reject / partial-accept 即可。

## 术语

### Q: evidence_strength 的 strong / medium / weak / stale 怎么区分？
- **strong[强]**：本轮 fresh 命令输出直接证明 AC 满足
- **medium[中]**：间接证据或部分覆盖（如只测了核心路径未测边界）
- **weak[弱]**：推理、代码审查或旧测试结果
- **stale[过期]**：之前轮次的证据，当前轮未重新验证

只有 strong 能标 met[满足]；medium 最多 partial[部分满足]；weak/stale 必须 not_met[未满足] 或 blocked[阻塞]。
