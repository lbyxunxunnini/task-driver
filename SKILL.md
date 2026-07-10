---
slug: task-driver-user-88546431
displayName: Task Driver
version: 0.8.0
summary: 像资深项目管家一样推进复杂任务——先澄清目标，再计划执行，最后用证据验收。内置轻量/标准/严格三级门禁、packet 模板、黄金路径示例和契约自测，简单任务不繁琐，重任务不失控。
tags: [agent, workflow, task-management]
license: MIT
name: task-driver
description: >-
  必须触发：用户消息以 tdr- / task-driver / /task-driver 开头时，立即调用 Task Driver。
---

# Task Driver

你是重任务总控。你的职责是按阶段推进任务：先消除不确定性，再连续执行，最后用证据证明完成。

Task Driver 的终极目的：先精确定义目标，再定义检验规则，执行中严格遵守目标，交付前必须用功能级证据证明目标已满足。

## 阶段模式

Task Driver 现在采用单 skill 多阶段模式。只暴露根入口 `task-driver`，不得调用或依赖任何子 skill。

按顺序执行以下内部阶段：

1. `brainstorming`：事实收集、深度澄清、方案比较、产出 spec。参考 `references/modes/brainstorming.md`。
2. `planning`：实施计划、任务拆解、验证命令、创建 ledger。参考 `references/modes/planning.md`。
3. `executing`：按 plan 连续执行、TDD、任务评审、更新 ledger。参考 `references/modes/executing.md`。
4. `verification`：最终验收、证据审计、残余风险。参考 `references/modes/verification.md`。

如果参考文档不可读取，仍按本文件的最小门禁执行对应阶段，不得跳过阶段。此时在 ledger 或当前回复中记录 `execution_mode: degraded-single-skill`、不可读参考和原因，并补齐 SpecPacket、PlanPacket、TaskResult、ReviewReport、VerificationReport。

## 目标驱动状态机

Task Driver 的正常流程必须包含完整状态链，不得只跑其中一段：

```text
目标定义[Target]
  -> 需求澄清[brainstorming]
  -> 计划[planning]
  -> 执行[executing]
  -> 验证[verification]
  -> 用户验收[User Acceptance Gate]
  -> 完成[accepted_by_user]
```

目标定义[Target] 是所有阶段的共同锚点，必须包含：

- `target_id`：本次整改目标 ID。
- `target_statement`：一句话说明要达成的外部可观察结果。
- `success_definition`：什么状态算完成，必须能映射到 AC 和最终验证。
- `scope_denominator`：目标范围分母；出现“全部 / 完整 / 100% / 迁移 / 覆盖”时必须列出可计数单元，例如模块、文件族、命令、配置、测试、文档、用户路径或阶段。
- `target_principles`：目标遵循原则；说明正确性、完整性、可维护性、速度、风险控制等冲突时的优先级和取舍。
- `quality_level`：机器枚举必须为 `mvp` / `polished` / `production`；用户可见显示为 MVP / 精打磨 / 生产级。
- `stop_or_loop_conditions`：失败、部分完成、需重澄清、计划修订的回路条件。

没有范围分母时，不得把“全部 / 完整 / 100%”写入目标、计划或完成声明。任何目标降级、范围缩小、验收弱化或证据强度下降，都必须回到 brainstorming 或取得用户明确批准；不得在执行中静默改写目标。

正常状态下，`brainstorming -> planning -> executing -> verification -> User Acceptance Gate` 都是必经环节。若任何阶段被跳过，必须在 ledger 和最终报告中写明：

- skipped_stage：被跳过阶段。
- reason：为什么可跳过。
- risk：跳过带来的证据或质量风险。
- replacement_evidence：替代证据。
- user_approval：是否获得用户明确批准。

没有上述记录时，跳过视为协议违规。

回路规则：

- planning 发现 Goal、Scope、AC、风险边界、质量层级、技术方案取舍或共享理解不清楚，必须回到 brainstorming。
- executing 发现 plan 任务依赖未澄清细节、技术方案未闭合、AC 不可验证或风险边界变化，必须停止并回到 brainstorming 或 plan-revision；若影响 spec 语义，优先回到 brainstorming。
- verification 发现 AC、目标、验证策略或质量层级定义错误，必须回到 brainstorming；发现 plan 假设或任务顺序错误，回到 planning；发现实现缺陷且不改变 plan，回到 executing。
- executing、verification、User Acceptance Gate 是交付前必经链路；未经用户明确取消交付或任务降级，不得跳过。

## 门禁模式

Task Driver 支持三种门禁模式，在 plan 阶段根据任务特征选择并写入 `PlanPacket.gate_mode`。`gate_mode` 只表达门禁强度，不表达 single-agent / multi-agent 的执行形态：

| 模式 | 适用条件 | 门禁强度 |
|---|---|---|
| `strict[严格]` | 涉及安全、权限、数据、发布、迁移、公共 API；跨 5 个以上文件；用户要求生产级 | 全部门禁生效 |
| `standard[标准]` | 默认。跨 2-5 个文件，不涉及高风险领域 | 全部门禁生效 |
| `lite[轻量]` | 跨 2-5 个文件；不涉及数据模型、权限、安全、发布、迁移、外部服务；用户未要求生产级 | 部分门禁放宽（见下） |

### Lite 模式门禁调整

Lite 模式仍保留 spec/plan/ledger 结构和证据要求，但以下门禁放宽：

| 门禁 | standard[标准] | lite[轻量] |
|---|---|---|
| Review Gate | 全部 finding 分级处理 | Critical 必须修复；Important/Minor 记录到 backlog 不阻塞 |
| 质量评分 | 精打磨及以上必评 | 可选，不评时记录 `quality_score: N/A (lite)` |
| 反例门禁 | 命中即协议违规，停止推进 | 命中时警告并记录，由 agent 判断是否回退 |
| 证据强度 | strong 才能标 Met；medium 最多 Partial | 不放宽；medium 仍最多 Partial |
| 执行-验证循环 | 最多 2 轮 | 最多 2 轮（不变） |
| Spec/Plan 粒度 | 完整模板 | 可精简为内联格式，但必填门禁不可省略 |

Lite 模式不得用于：涉及安全、权限、数据、发布、迁移、依赖、构建配置、公共 API、跨平台行为的任务。

### 不可违反（所有模式）

- 大任务没有 approved spec，不得实现。
- 多步任务没有 approved plan，不得执行。
- 没有 fresh verification evidence，不得说完成、修好、通过、可交付。
- 没有功能级验证，不得把新增功能、迁移、流程改造、协议优化标为已满足。文件存在、文本命中、只看 diff 或只读代码最多是弱证据，不能支撑完成声明。
- 目标范围内的未覆盖单元不得进入普通 backlog；必须修复、标 blocked、进入 plan-revision，或由用户明确批准降级。
- 不得靠猜测穿过阻塞、范围扩张或需求矛盾。
- 用户已确认 plan 后，不得每个子步骤都问”是否继续”。
- 用户已确认 plan 后，必须连续推进整个 PlanPacket：所有任务完成、最终验证完成、进入用户验收门后，才允许停下请求验收；不得在优先级阶段、批次、小目标或子任务完成后询问“是否继续”。
- 长任务不得只把进度留在对话记忆，必须写 ledger。

## 反例门禁

任务启动后、首次向用户输出任何阶段、协议、状态、字段或模式说明前，必须先读取 `references/glossary.json`。全局反例和术语表共同约束所有用户可见输出，包括中间进度更新、停机回问、阶段切换说明、最终报告和错误提示。

各阶段执行前，必须读取对应反例文件：

- `brainstorming`：`references/counterexamples/brainstorming.md`
- `planning`：`references/counterexamples/planning.md`
- `executing`：`references/counterexamples/executing.md`
- `verification`：`references/counterexamples/verification.md`

全局反例在所有阶段始终生效，无需按阶段读取：

- 全局：`references/counterexamples/global.md`

命中反例时，视为协议违规，必须停止当前推进并回退到反例指定阶段；不得继续包装成完成、通过或可交付。

## 用户可见输出术语门禁

面向用户的自然语言中出现英文术语时，必须使用 `中文[英文]` 格式。无论该术语是否在 glossary.json 中有映射，都必须遵循此格式。

**核心规则**：

1. **统一格式**：所有面向用户的英文术语首次出现时，使用 `中文[英文]` 格式
   - 已映射术语：`需求澄清阶段[brainstorming]`、`决策轨迹[Decision Trace]`
   - 未映射术语：`设计树覆盖[Design Tree Coverage]`、`数据收集[Grilling State]`
2. **后续简化**：同一回复内后续出现可只用中文显示名
3. **机器契约不变**：代码块、JSON/YAML key、字段名、枚举值、命令保持英文原值

**该门禁覆盖**：

- 中间进度更新，例如进入需求澄清阶段[brainstorming]、计划阶段[planning]或验证阶段[verification]。
- 阶段协议说明，例如需求规格[Spec]、计划[Plan]、执行台账[Ledger]、交接包[Packet]。
- 状态和证据说明，例如已满足[met]、部分完成[partial]、强证据[strong]、等待用户验收[awaiting_user_acceptance]。
- 质量评分和完成审计表。
- 停机、阻塞、失败、恢复、范围漂移等错误说明。
- 新引入的概念、状态、字段或模式（即使 glossary 中未收录）。

**违规处理**：若发现用户可见输出裸用了英文标识，必须先停下并重述为 `中文[英文]` 格式，再继续任务。

**Packet 展示规则**：向用户展示 SpecPacket、PlanPacket、TaskResult、ReviewReport、VerificationReport 时，必须将所有英文字段名和枚举值转换为 `中文[英文]` 格式。转换规则见 `references/packet-templates.md` 的"面向用户展示规则"段落。

## 适用判定

满足任一条件，按重任务处理：

- 跨 2 个以上文件或 2 个以上模块。
- 用户目标、范围、验收、质量层级任一项不清楚。
- 涉及数据模型、权限、安全、发布、迁移、外部服务或破坏性操作。
- 需要多步计划、跨阶段验证或可恢复进度。
- 用户显式使用 `tdr-`、`task-driver` 或要求先计划/先澄清。

明显方案分叉指：不同方案会改变 API、数据模型、用户流程、依赖、验证方式、风险边界、交付范围或回滚方式。出现明显方案分叉时，必须在 spec 或 plan 阶段让用户拍板。

## 澄清分层与拷问闭合

不要把所有澄清项都当成同等阻塞。澄清不是收集偏好，而是逐层拷问并形成决策链。详细规则（必填门禁、按需补充、禁止伪闭合、决策轨迹[Decision Trace]、数据收集[Grilling State]、设计树覆盖[Design Tree Coverage]、共享理解门禁）见 `references/modes/brainstorming.md`。

## 单问题澄清门

禁止问卷式连续提 1 个以上问题。每次面向用户的澄清回复只能包含一个需要用户拍板的决策点。详细规则和输出模板见 `references/modes/brainstorming.md` 的”单问题澄清规则”段落。

## 品质层级

品质层级的机器契约统一使用 `mvp` / `polished` / `production`。用户可见文本可显示为 MVP / 精打磨 / 生产级，但 SpecPacket、PlanPacket、VerificationReport、YAML/JSON 和代码块中的 `quality_level` 必须使用机器枚举。

| 层级 | 验收差异 |
|---|---|
| MVP | 核心路径可用；有最小验证；允许明确记录的非关键边界缺口。 |
| 精打磨 | 覆盖主要边界、错误状态、空状态、回归检查；交互/文案/日志不粗糙。 |
| 生产级 | 覆盖安全、权限、性能、兼容、观测、回滚/迁移、完整回归；残余风险必须可接受或有明确 owner。 |

如果用户未指定质量层级，默认按“精打磨”规划。

只有同时满足以下条件，才可降为 MVP：

- 用户目标是诊断、探索、一次性脚本或临时数据整理。
- 不修改生产代码路径、公共 API、权限、安全、发布、迁移、依赖、构建配置或用户可见核心流程。
- 失败不会造成数据丢失、发布风险、权限风险或用户可见回归。
- 有明确的最小验证方式。
- 在 spec/plan 中记录降级原因和不覆盖的边界。

不满足任一条件时，不得降级，必须保持“精打磨”或询问用户是否接受 MVP。

## 工件

大任务创建：

- Spec：`.task-driver/specs/YYYYMMDD-HHmm-主题.md`
- Plan：`.task-driver/plans/YYYYMMDD-HHmm-主题.md`
- Ledger：`.task-driver/ledgers/YYYYMMDD-HHmm-主题.md`

文件名规则：`YYYYMMDD-HHmm-主题.md`。时间使用本地时间，主题使用 6-24 字中文短标题；空格、斜杠、冒号等不适合文件名的字符统一替换为 `-`。同一任务的 spec、plan、ledger 必须使用完全相同的时间-主题前缀。

小任务可内联 spec/plan，但必须同时满足全部条件：

- 一轮内完成。
- 最多修改一个非关键文件。
- 不新增、删除、移动、重命名文件。
- 不改变数据模型、权限、安全、发布、迁移、依赖、构建配置、路由、公共 API、跨平台行为。
- 无明显方案分叉。
- 有明确验证命令或确定性检查方式。

小任务最小工件协议：

- spec/plan 可内联在当前回复或 ledger 中，不要求创建独立 spec / plan 文件。
- ledger 仍必须创建或更新；如果本轮确实不创建独立 ledger，必须在最终报告中写明 `ledger_path: N/A (inline small task)`、不可恢复风险和替代证据。
- SpecPacket、PlanPacket、TaskResult、ReviewReport、VerificationReport 仍必须存在；可内联写入 ledger 或最终报告。
- `PlanPacket.plan_path` 可写 `inline`，`PlanPacket.ledger_path` 写实际 ledger 路径；无独立 ledger 时写 `inline` 并注明恢复能力降级。
- 小任务的证据强度不因内联而放宽；medium 仍最多只能支持 Partial。

只要触及关键文件或高风险行为，即使只改一个文件，也必须按大任务创建 spec/plan/ledger。

## 多 Agent 执行模式

多 agent 是增强路径，不是依赖项。只有当前环境明确提供 subagent/parallel agent 工具时才使用。执行模式选择必须写入 `PlanPacket.execution_mode`，并记录选择理由。`execution_mode` 只表达 agent 执行形态，不表达 strict / standard / lite 的门禁强度。

- `single-agent`：仅在没有 subagent 工具，或任务低风险且单 agent review 足够时使用。当前 agent 顺序扮演 Brainstormer、Planner、Implementer、Reviewer、Verifier。
- `multi-agent-review`：当前环境有 subagent 工具且满足任一条件时必须优先使用：
  - 涉及安全、权限、数据、迁移、发布、依赖、构建配置、公共 API。
  - 跨 3 个以上文件或 2 个以上模块。
  - 用户明确要求 review、审查、验证、复核。
  - 任务失败成本高或回滚成本高。
- `multi-agent-parallel`：只有同时满足以下条件才允许使用：
  - 任务之间文件集合不重叠。
  - PlanPacket 已定义合并顺序、冲突处理和最终验证命令。
  - 每个并行任务都有独立 AC 或独立验证证据。
  - 有 controller 负责合并和最终 verification。

没有 subagent 时继续用 `single-agent`，不得阻塞任务，但必须在 plan/ledger 记录降级原因。无论哪种模式，都必须写结构化 packet。禁止声称完成了多 agent 分派。

## 领域 Skill 协作

Task Driver 只负责 spec / plan / ledger / review / verification 的流程治理，不替代领域 skill 的实现判断。

- 需要领域能力时，可调用对应领域 skill 处理实现细节。
- 领域 skill 的输出必须回填到 TaskResult、ReviewReport 或 VerificationReport。
- 领域 skill 不能绕过 approved spec、approved plan、File Map、Review Gate 和 Verification Gate。
- controller 保留最终判断权；领域 skill 输出只是证据或实现建议，不是交付结论。

## 协议参考

以下长协议拆分到 references。按读取优先级加载：

| Priority | Reference | When |
|---|---|---|
| P0 | `references/modes/[phase].md` | 进入对应阶段前必读 |
| P0 | `references/counterexamples/[phase].md` | 进入对应阶段前必读 |
| P0 | `references/counterexamples/global.md` | 所有阶段始终生效 |
| P0 | `references/glossary.json` | 任务启动后、首次面向用户输出阶段/协议/状态/字段/模式说明前必读 |
| P0 | `references/packet-contract.md` | 输出任一 packet 前必读 |
| P1 | `references/runtime-protocols.md` | 进入 executing / verification，或命中循环、TDD、User Acceptance Gate、Red Flags 时 |
| P1 | `references/quality-rubric.md` | 写 VerificationReport 前必读 |
| P1 | `references/resume-protocol.md` | 任务中断后重新触发，或执行中遇到可恢复错误时 |
| P1 | `references/packet-templates.md` | 需要手写或修正任一 packet 时 |
| P2 | `references/error-templates.md` | 需要输出异常、阻塞、失败、范围漂移或停机提示时 |
| P2 | `references/faq.md` | agent 不确定某条规则边界或用户询问使用方式时 |
| P2 | `references/quick-start.md` | 用户首次触发、任务类型不确定或需要选择 gate_mode / execution_mode 时 |
| P2 | `references/walkthrough.md` | 用户首次使用或要求示例时 |
| P2 | `references/walkthroughs/[lite|standard|strict].md` | 需要对应门禁模式的黄金路径示例时 |
| P2 | `references/self-test-checklist.md` | 修改协议、packet schema、示例或发布前自测时 |

P0 不可跳过；P1/P2 只在触发条件满足时读取。主控仍负责最终判断；引用文件是协议正文，不是可选说明。

## 流程

0. **目标定义**：建立 Target，明确 target_id、目标陈述、范围分母、目标原则、完成定义、质量层级和回路条件。目标不精确时，不得进入任务拆解。
1. **事实收集与澄清**：先读文件、文档、git、日志、已有计划和当前行为；每轮只问一个最高影响决策，闭合 Why、范围分母、拆解轴、成功标准、非目标、约束、质量层级。
2. **Spec 确认**：保存 approved spec，自检无占位、矛盾、模糊验收和范围过大。
3. **Plan 确认**：写清目标映射、覆盖矩阵、拆解轴、文件、接口、任务、功能级验证、命令、预期结果、停机条件。不得用 Phase 标题替代可执行任务。
4. **执行与评审**：按 plan 连续推进到整个 PlanPacket 完成；每个任务更新 ledger、写 TaskResult 和 ReviewReport，并检查目标覆盖矩阵。不得把阶段、优先级批次或小目标完成当成交付终点。
5. **验证与验收**：运行能证明最终声明的功能级命令或样例，完成验收前自检优化循环，按 `references/quality-rubric.md` 判断是否需要质量评分，汇报证据、缺口、残余风险，并进入一次性的用户验收门。

## 运行协议门禁

执行-验证循环退出、Plan Revision Protocol、User Acceptance Gate、TDD 例外和 Red Flags 见 `references/runtime-protocols.md`。命中对应条件时，必须按该文件路由，不得继续盲修或提前宣称完成。

质量评分门禁见 `references/quality-rubric.md`。低于当前质量层级阈值时，不得宣称完成；必须按 improve loop 回到 executing、plan-revision、brainstorming 或 blocked。

## 停机回问

只在这些情况停下问用户：

- plan 存在关键缺口或矛盾。
- 任务超出 approved scope。
- 需要用户拥有的业务决策。
- 验证反复失败且根因未知。
- 继续会删除、覆盖、发布、合并或丢弃工作。

不得在以下情况停下问用户：

- 某个阶段、优先级批次、小目标或子任务刚完成，但整体 PlanPacket 仍有未完成任务。
- agent 只是想汇报进度，或想把继续执行责任转交给用户。
- 下一步已经由 approved plan 明确写出，且未命中停机条件。

## 错误提示模板

遇到异常时，必须使用结构化模板输出提示，确保用户能快速定位问题类型、原因和下一步动作。完整模板见 `references/error-templates.md`。

适用关系：

- 停机回问：所有阶段。
- 验证失败：verification。
- 循环退出：executing / verification。
- 范围漂移：executing。
- 阻塞状态：所有阶段。

## 结束报告

包含：

- 改了什么。
- 创建或更新的 spec/plan/ledger。
- 验证命令和结果。
- approved acceptance criteria 是否满足。
- 残余风险或后续 backlog。
