# Global Counterexamples

这些反例在所有阶段生效，命中时视为协议违规，必须停止当前推进并回退；不得继续包装成完成、通过或可交付。

## 面向用户输出使用英文原值

- 错误：完成审计表、质量评分表等面向用户的输出中，状态值、证据强度、维度名直接使用英文原值（如 `Met`、`Partial`、`strong`、`Correctness`），未按 glossary 规则翻译。
- 违规：违反 glossary.json "面向用户输出时，优先使用中文显示名"规则，所有面向用户的输出必须使用 `中文显示名[英文标识]` 格式。每个阶段视为独立上下文：同一阶段内首次出现使用完整 `中文[英文]` 格式，后续可只用中文显示名。
- 回退：逐项检查输出中的协议标识、状态值、字段名；glossary.json 已收录的直接替换为 `中文[英文]`；未收录的由 agent 自行翻译后使用 `中文[英文]` 格式输出。

## 未映射术语裸用英文

- 错误：面向用户输出中出现 glossary.json 未收录的英文术语（如 `Design Tree Coverage`、`Grilling State`、`SpecPacket`），直接使用英文原值，未使用 `中文[英文]` 格式。
- 违规：用户可见输出术语门禁要求所有英文术语（无论是否在 glossary 中有映射）首次出现时使用 `中文[英文]` 格式。不能以"glossary 中没有映射"为由裸用英文。
- 回退：立即将裸用的英文术语改为 `中文[英文]` 格式（如 `设计树覆盖[Design Tree Coverage]`、`数据收集[Grilling State]`），然后继续任务。

## Packet 展示裸用字段名

- 错误：向用户展示 SpecPacket、PlanPacket、TaskResult、ReviewReport 或 VerificationReport 时，字段名直接使用英文原值（如 `spec_path`、`approved_by_user`、`status`、`quality_level`），未转换为 `中文[英文]` 格式。
- 违规：Packet 是机器契约，但面向用户展示时必须转换字段名和枚举值。`spec_path` 应显示为 `需求规格路径[spec_path]`，`approved_by_user` 应显示为 `用户已确认[approved_by_user]`，`status: approved` 应显示为 `状态[status]: 已确认[approved]`。
- 回退：停止当前输出，按 `references/packet-templates.md` 的"面向用户展示规则"重新格式化 packet 内容，然后继续任务。

## 阶段交接裸贴机器契约

- 错误：需求澄清阶段结束后，面向用户直接输出 `spec_path: inline`、`target_id: ...`、`evaluation_result:`、`go:`、`no_go:`、`shared_understanding: true`，再询问"下一步开始实现还是到此为止"。
- 违规：阶段交接、计划前确认、停机回问和评估结论属于用户可见 Packet 展示，不得裸贴 YAML/JSON 风格机器契约。扩展字段同样必须按 `中文[英文]` 格式渲染，并使用分组表格或清单展示。
- 回退：将评估结论渲染为 `评估结论[evaluation_result]` 表格，将 SpecPacket 摘要渲染为分组表格，将下一步动作渲染为 `下一步决策[next_step]` 表格。

## 目标模式过早激活

- 错误：brainstorming 还没有 approved SpecPacket，就调用 Codex create_goal 或输出 Claude Code `/goal`。
- 违规：Goal 必须由已确认 Target 派生；未确认 spec 的目标可能会固化错误范围、验收或风险边界。
- 回退：清理或暂停未确认目标；回到 brainstorming 完成 SpecPacket 和 shared_understanding，再在 planning 生成 GoalDraft。

## 静默覆盖已有 Goal

- 错误：发现 Claude Code 或 Codex 已有 active goal，直接发送新的 `/goal` 或 create_goal 替换当前目标。
- 违规：Claude Code 新 `/goal` 会替换旧 goal；Codex Goal 也属于线程级完成契约。target_id 不一致时必须停机回问，不得静默覆盖用户已有目标。
- 回退：展示当前目标冲突、当前 Task Driver target_id 和建议选项；用户确认前降级为 `ledger-only` 或暂停执行。

## 证据不足就完成 Goal

- 错误：测试未覆盖全部 AC、target_coverage 缺失或仅有 diff 审查，就调用 `update_goal(status=complete)`，或把 Claude Code goal 自动 clear 当作任务完成。
- 违规：Goal complete 必须由 VerificationReport 的当前证据证明；Goal 达成不等于用户验收。
- 回退：回到 verification 补 Goal complete gate；证据不足则回到 executing、plan-revision、brainstorming 或 blocked。

## 同上下文自证目标完成

- 错误：实现者在同一上下文中读完自己刚写的 VerificationReport 后，直接判断 GoalDraft 已满足并标记 complete。
- 违规：目标检测[goal_detection]必须由隔离上下文的子智能体[subagent]或等价 isolated verifier 执行；当前执行上下文不能自证目标完成。
- 回退：将 SpecPacket、GoalDraft、PlanPacket、ledger evidence、VerificationReport 草稿和必要命令输出交给 isolated_goal_verifier；没有 subagent 时可降级为新会话、外部工具或人工隔离审查，但不得降级为同上下文自检。没有任何隔离检测路径时不得 complete，必须 blocked、回到 verification 或请求外部验证。

## 阶段进度说明裸用英文阶段名

- 错误：面向用户说“进入 brainstorming 阶段”“补读 planning 协议”“进入 verification”或“执行 executing 阶段”，未使用中文显示名。
- 违规：阶段名属于面向用户的模式名/阶段名，必须按 glossary 使用 `需求澄清阶段[brainstorming]`、`计划阶段[planning]`、`执行阶段[executing]`、`验证阶段[verification]`。中间进度更新、阶段切换说明和停机回问都属于用户可见输出。
- 回退：停止继续推进，读取 `references/glossary.json`，重述当前阶段和后续动作；之后同一回复内可只用中文显示名。

## 解释协议或阶段前未读取术语表

- 错误：在未读取 `references/glossary.json` 的情况下，向用户解释 spec、plan、ledger、packet、brainstorming、planning、executing、verification、strict、standard、lite 等协议、阶段或模式。
- 违规：触发术语显示规则但未加载术语表，导致中文显示名不稳定。`references/glossary.json` 是任务启动后、首次面向用户输出阶段/协议/状态/字段/模式说明前的 P0 必读文件。
- 回退：立即读取 `references/glossary.json`；重新输出用户可见说明。机器契约、路径、YAML/JSON key、枚举值、命令和代码块保持英文原值。

## 把机器契约中文化

- 错误：为了遵守中文显示名，把 YAML key、JSON key、枚举值、命令、文件路径或代码块里的 `status`、`mode`、`accepted_by_user`、`.task-driver/...` 改成中文。
- 违规：glossary 只约束面向用户的显示方式，不允许修改机器契约。机器契约必须保持英文原值，否则会破坏 packet、脚本、路径或验证命令。
- 回退：恢复机器契约英文原值；只在代码块外、表格说明或自然语言解释中使用中文显示名。

## 固定话术压过自然澄清

- 错误：每次澄清都使用“只需要你拍板 1 个问题”作为标题或口头禅。
- 违规：单问题澄清门要求每轮只有一个决策点，不要求使用生硬话术。该表达只适合最终收口且确实只剩最后一个阻塞问题时使用。
- 回退：改为自然直接的问题标题，例如“请确认：...”，并保留已知事实、当前层级、选项、推荐和下一步。

## 阶段性完成后转交继续责任

- 错误：`P0 阶段全部完成，当前进度 5/25，下一步进入 P1，是否继续？`
- 违规：用户已确认 plan 后，agent 必须连续推进整个 PlanPacket。优先级阶段、批次、小目标或子任务完成不是停机条件。
- 回退：更新 ledger 和进度说明后，自动进入下一个 pending task；只有命中停机条件或最终用户验收门时才回问。

## 跳过必经状态

- 错误：没有 brainstorming / planning / executing / verification / User Acceptance Gate 中的某一环，就声称交付完成，且没有记录跳过原因。
- 违规：正常状态链必须完整；跳过必须写 `skipped_stage / reason / risk / replacement_evidence / user_approval`。
- 回退：回到缺失的最早阶段补齐；若确实跳过，写明原因、风险、替代证据和用户批准。

## 没有目标锚点

- 错误：只按任务清单推进，没有 `target_id`、目标陈述、完成定义和回路条件。
- 违规：后续计划、执行、验证无法判断是否围绕同一目标完成。
- 回退：回到 brainstorming 补 Target，并让 plan / ledger / verification 引用同一 target_id。

## 目标分母缺失

- 错误：使用“全部 / 完整 / 100% / 迁移 / 覆盖”描述目标，但没有列出模块、文件族、命令、配置、测试、文档、用户路径或阶段分母。
- 违规：没有 scope_denominator 就无法证明完整性，也无法判定是否偷懒。
- 回退：回到 brainstorming 确认范围分母和完成判定。

## 静默降低目标

- 错误：目标是“完整迁移 / 100% 覆盖 / 全部整改”，执行中只完成一部分，最终报告改成“核心完成”或“主要完成”。
- 违规：目标降级必须用户明确批准，并写入 Decision Trace、ledger Decisions 和 VerificationReport.unmet_requirements[]。
- 回退：停止完成声明；按目标分母补齐覆盖矩阵，未覆盖项进入 executing、plan-revision、brainstorming 或 blocked。

## 读完协议后直接执行

- 错误：读完 SKILL.md、glossary.json 或 references 后，直接说"好的，我理解了，现在开始改"或"我现在进入执行阶段"，没有先走 brainstorming 和 planning。
- 违规：读取协议是准备动作，不等于已通过 brainstorming 和 planning。协议读取完成后仍必须按状态链推进：Target → brainstorming → planning → executing → verification。
- 回退：停止执行意图；回到 brainstorming 开始事实收集和需求澄清。

## 口头计划替代已确认计划

- 错误：agent 口头描述"我打算先改 A 再改 B 再改 C"，用户说"好的"，agent 就开始执行，没有产出结构化的 PlanPacket 或内联 plan 并让用户明确确认。
- 违规：自然语言对话中的"计划"不是 approved plan。approved plan 必须是结构化的 PlanPacket（或内联等价物），且有用户明确确认记录。
- 回退：停止执行；将口头计划转化为结构化 PlanPacket 或内联 plan，提交用户确认后才能解除写入屏障。

## 预热创建工件目录

- 错误：还没有 approved spec 和 approved plan，就先执行 `mkdir -p .task-driver/specs` 或 `mkdir -p .task-driver/plans`，声称"只是预热目录"。
- 违规：目录创建是写入动作，受写入屏障约束。没有 approved spec 且没有 approved plan 时，`.task-driver/` 下任何目录都不得创建。
- 回退：删除预创建的目录（或记录为已存在）；等 spec/plan 确认后再创建。

## 弱证据包装完成

- 错误：用文件已创建、文本已写入、`rg` 命中或 diff 看起来正确，宣布功能、迁移、协议或流程已完成。
- 违规：文件存在和文本命中默认是 weak evidence，不能支撑 met 或完成声明。
- 回退：补功能级验证、样例任务、反例检查、端到端流程或明确证据强度上限；无法补强时标 partial / blocked。
