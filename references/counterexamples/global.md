# Global Counterexamples

这些反例在所有阶段生效，命中时视为协议违规，必须停止当前推进并回退；不得继续包装成完成、通过或可交付。

## 面向用户输出使用英文原值

- 错误：完成审计表、质量评分表等面向用户的输出中，状态值、证据强度、维度名直接使用英文原值（如 `Met`、`Partial`、`strong`、`Correctness`），未按 glossary 规则翻译。
- 违规：违反 glossary.md "面向用户输出时，优先使用中文显示名"规则，所有面向用户的输出必须使用 `中文显示名[英文标识]` 格式。每个阶段视为独立上下文：同一阶段内首次出现使用完整 `中文[英文]` 格式，后续可只用中文显示名。
- 回退：逐项检查输出中的协议标识、状态值、字段名；glossary.md 已收录的直接替换为 `中文[英文]`；未收录的由 agent 自行翻译后使用 `中文[英文]` 格式输出。

## 阶段进度说明裸用英文阶段名

- 错误：面向用户说“进入 brainstorming 阶段”“补读 planning 协议”“进入 verification”或“执行 executing 阶段”，未使用中文显示名。
- 违规：阶段名属于面向用户的模式名/阶段名，必须按 glossary 使用 `需求澄清阶段[brainstorming]`、`计划阶段[planning]`、`执行阶段[executing]`、`验证阶段[verification]`。中间进度更新、阶段切换说明和停机回问都属于用户可见输出。
- 回退：停止继续推进，读取 `references/glossary.md`，重述当前阶段和后续动作；之后同一回复内可只用中文显示名。

## 解释协议或阶段前未读取术语表

- 错误：在未读取 `references/glossary.md` 的情况下，向用户解释 spec、plan、ledger、packet、brainstorming、planning、executing、verification、strict、standard、lite 等协议、阶段或模式。
- 违规：触发术语显示规则但未加载术语表，导致中文显示名不稳定。`references/glossary.md` 是任务启动后、首次面向用户输出阶段/协议/状态/字段/模式说明前的 P0 必读文件。
- 回退：立即读取 `references/glossary.md`；重新输出用户可见说明。机器契约、路径、YAML/JSON key、枚举值、命令和代码块保持英文原值。

## 把机器契约中文化

- 错误：为了遵守中文显示名，把 YAML key、JSON key、枚举值、命令、文件路径或代码块里的 `status`、`mode`、`accepted_by_user`、`docs/task-driver/...` 改成中文。
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
