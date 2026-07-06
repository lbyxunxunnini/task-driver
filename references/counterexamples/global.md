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
