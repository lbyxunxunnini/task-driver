# Brainstorming Mode

需求澄清与 spec 阶段。用于 task-driver 开工前：事实收集、深度澄清、方案比较、明确范围/非目标/验收/质量层级，并产出 approved spec 与 SpecPacket。

把粗糙请求变成 approved spec。此阶段不得写实现代码，不得脚手架化方案，也不得直接输出最终实施计划。

## 必做清单

1. 读取当前事实：文件、文档、git 状态、日志、报错、已有 spec/plan、相关命令。
2. 判断任务是否过大；过大时先识别任务类型，再拆第一片。
   - 若用户目标是“重新规划 / 整体规划 / 重构规划 / 从头梳理 / 重新设计”，第一片必须是规划框架片：目标、大类、范围边界、优先级和验收产物，不得直接拆到实现细节。
   - 若用户目标是功能实现或 bugfix，第一片必须覆盖一个可验证的端到端用户价值或最小复现闭环，不得只拆内部技术步骤。
   - 拆第一片前必须说明为什么该片最能降低不确定性或交付风险。
3. 建立目标草案并持续更新：每轮澄清都必须说明本轮决策如何改变 target_statement、scope_denominator、target_principles、success_definition 或 AC；不得等所有 Phase 都讨论完后一次性补目标。
4. 禁止问卷式连续提 1 个以上问题；每轮只问一个最高影响决策点，直到决策树闭合。
5. 多方案时给出 2-3 个方案、取舍和推荐；禁止只抛开放问题。
6. 展示 spec，并取得用户确认。
7. 保存 approved spec：`.task-driver/specs/YYYYMMDD-HHmm-主题.md`。
8. 按 `SKILL.md` 的 packet contract 输出 SpecPacket。
   - 如果 ledger 已存在，必须写入 ledger。
   - 如果 ledger 尚未创建，必须写入 spec 末尾的 `## SpecPacket` 或 planning handoff，并在 planning 创建 ledger 时同步复制。
   - 禁止只把 SpecPacket 留在对话记忆或未持久化草稿中。
   - planning 阶段创建 ledger 前必须检查 SpecPacket 是否已持久化；未持久化不得进入 plan 编写。
9. 自检 spec：无占位、矛盾、模糊验收、范围漂移、目标分母缺失、功能级验证缺失。

## 澄清标准

按主控的“澄清分层”和“品质层级”执行。必填门禁必须闭合；按需补充项只有经事实收集和影响判断确认不影响方案或验收时，才可标 `N/A`，并必须写明判断依据；否则必须补齐。

必填门禁：

- Why：用户真实场景和期望收益。
- What：核心交付物和 2-5 个关键行为。
- Success：具体验收标准和证据来源。
- Quality：MVP / 精打磨 / 生产级。
- Scope：包含内容和明确非目标。
- Constraints：技术、时间、安全、合规、平台、风格、依赖限制。
- Target denominator：出现“全部 / 完整 / 100% / 迁移 / 覆盖”时，必须列出可计数范围分母。
- Target principles：冲突时按什么原则取舍，例如完整性优先于速度、功能验证优先于文本存在检查。
- Verification rule：每条 AC 的功能级检验方式；文件存在、文本命中或只看 diff 只能作为弱证据，不得作为完成证明。

按需补充：

- User：使用者和能力水平。
- Trade-offs：可裁剪项和不可裁剪项。
- Risks：风险和缓解。

只问会改变 spec 或决定 spec 生成路径的问题。对重新规划、整体规划、重构规划、从头梳理、重新设计类任务，规划视角、大类划分、范围切片和优先级都属于 spec 生成路径问题，必须按单问题澄清规则逐层闭合。能给参考答案时，必须给 2-3 个互斥选项和推荐答案，帮助用户决策；禁止借口“不能给参考答案”退回开放式提问。

技术方案选项也必须服从澄清层级。若方案会改变接口、数据模型、依赖、文件边界、验证方式、回滚方式、用户流程或风险边界，它不是 plan 细节，而是 spec 生成路径的一部分；必须停留在 brainstorming，通过单问题澄清逐层闭合。不得在目标、范围、验收、风险和取舍轴尚未闭合时，把技术方案拆成任务并进入 executing。

## 精准目标门禁

目标不是最后生成 spec 时才写的总结，而是从第一轮澄清开始持续收紧的契约。每次用户决策后，必须更新目标草案中的至少一个字段，或说明该决策不影响目标契约的原因。

目标契约必须回答：

- 外部可观察结果：完成后用户、系统、文档、流程或仓库状态发生什么可验证变化。
- 范围分母：本轮目标包含哪些可计数单元，尤其是模块、文件族、命令、配置、测试、文档、用户路径、阶段或协议条款。
- 完成比例定义：出现“100% / 全部 / 完整 / 迁移 / 覆盖”时，必须写出分母总数、每个单元的完成判定和允许遗漏条件。
- 目标原则：正确性、完整性、可维护性、速度、风险控制、用户体验发生冲突时按什么优先级取舍。
- 降级规则：什么情况必须回到 brainstorming、plan-revision 或 blocked；哪些降级必须用户批准。

如果无法列出范围分母，不得把目标写成“全部完成”“完整迁移”“100% 覆盖”。如果用户坚持这类目标，必须先用单问题澄清门确认分母口径。

## 拆解深度门禁

计划拆解前必须先闭合拆解轴和拆解粒度。不得从目标直接跳到 Phase、Step 或文件清单。

必须确认：

- 拆解轴：按阶段、模块、风险、用户路径、产物类型、协议层级、问题类型还是交付价值拆。
- 拆解层级：只到 Phase 是否足够；若要执行，必须继续拆到可验证任务、子任务、验证点和停机条件。
- 每层产物：每个拆解单元输出什么，交给下游什么。
- 每层验收：每个拆解单元如何证明完成，证据强度上限是什么。
- 未决设计点：哪些内容会改变目标、范围、AC、验证或风险，必须用户确认，不得由 agent 推荐后直接落地。
- 粒度下限：执行任务必须小到“文件 + 行为/内容变化 + AC 引用 + 功能级验证方式”明确。

若任务涉及评价标准、Rubric、评分、成熟度、checklist、阶段门禁或自检规则，必须把评价模型当作设计对象闭合：

- 评价对象：评什么、不评什么。
- 评价维度：维度来源、数量、是否有权重。
- 评分尺度：分值、等级或 pass/fail 规则。
- 通过阈值：什么状态算达标。
- 证据来源：功能样例、命令、人工审查表、反例用例或文件检查。
- 失败反例：什么样的产物必须判为不达标。

这些口径会影响 AC 或验证强度时，必须由用户确认或写为有依据的 assumption；不得在 planning 中自行补默认值。

## 拷问细化协议

本阶段必须建立决策轨迹[Decision Trace]。它记录从宏观到细节的拷问链，证明 agent 不是跳到技术方案或任务拆解，而是和用户逐层达成一致。

### Grilling State

数据收集不是一次性表格填写，而是一个交互状态机。进入 brainstorming 后，必须在对话或 ledger 中维护当前数据收集状态。

**面向用户必须展示的格式**（决策摘要）：

```markdown
---
**当前决策点**

- 当前层级：整体目标 / 大类划分 / 范围切片 / 小项目 / 行为细节 / 实现约束
- 已确认：[1-3 条已闭合决策]
- 未闭合：[影响目标、范围、AC、验证或风险的分支]
- 本轮只确认：[一个最高影响决策问题]
---
```

完整数据收集[grilling_state]表格只写入 ledger 或 spec；面向用户展示仅限用户主动要求时。不得每轮把完整内部状态表格作为默认输出。

**机器契约格式**（写入 ledger 或 spec 时使用）：

```yaml
grilling_state:
  current_branch: 整体目标 | 大类/规划轴 | 范围切片 | 小项目/模块 | 行为细节 | 实现约束
  current_question: [当前唯一问题]
  upstream_decisions: [已闭合的上游决策]
  dependency: [本问题依赖哪个上游决策]
  recommended_answer: [agent 推荐答案和理由]
  user_decision: pending | [用户选择]
  unresolved_branches: [尚未闭合的分支]
  shared_understanding: false
```

每轮只允许推进 `current_question`。用户回答后，必须先更新 `user_decision` 和 `upstream_decisions`，再选择下一条最依赖当前答案的分支。禁止在一个回复中同时推进多个分支。

### Design Tree Coverage

宏观到细分不是线性过一遍 6 个标题，而是沿设计树逐分支闭合。进入 spec 草稿前，必须建立设计树覆盖表：

```yaml
design_tree:
  root_goal: [target_statement]
  branches:
    - id: B1
      name: [分支名，例如范围切片/技术方案/验证策略/风险边界]
      parent: [上游分支或 root_goal]
      layer: 整体目标 | 大类/规划轴 | 范围切片 | 小项目/模块 | 行为细节 | 实现约束
      status: open | decided | deferred | out_of_scope
      decision_ref: [Decision Trace 行或 assumption_id]
      blocks: [被它阻塞的下游分支]
```

必须覆盖的分支类型：

- 目标分支：为什么做、为谁做、成功外观。
- 范围分支：本轮包含、明确排除、后续触发条件。
- 覆盖分母分支：目标单元、完成比例、遗漏处理和降级批准。
- 拆解分支：拆解轴、拆解层级、每层产物、每层验收和粒度下限。
- 行为分支：正常路径、错误路径、空状态、边界条件。
- 方案分支：关键技术方案、替代方案、拒绝理由。
- 验证分支：功能级验证、自动验证、人工验收、证据强度上限。
- 风险分支：安全、权限、数据、发布、迁移、回滚、兼容。

每个分支只能处于以下状态之一：

- `decided`：用户决策或合法 assumption 已记录，且影响已映射到 AC / Scope / Risks / Verification。
- `deferred`：不影响本轮 AC、风险边界和验证方式，有 owner、原因和后续触发条件。
- `out_of_scope`：明确写入 Non-Goals 或 rejected_paths。
- `open`：仍阻塞 spec；不得进入 planning。

只要存在 `open` 分支，就必须继续单问题拷问。不得只闭合主路径，留下错误路径、验证路径、风险路径或替代方案未问清。

### 事实与决策分离

- 事实问题：能从代码、文档、日志、git、已有 spec/plan/ledger 或命令输出查到的内容，必须先查；不得问用户。
- 决策问题：目标、优先级、范围边界、风险接受、方案取舍、质量层级、验收口径，必须问用户。
- assumption：只允许用于低风险、可逆、不影响 AC/风险/验证的细节；必须写明依据、验证点和回滚方式。

每个用户问题必须标注它为什么是决策问题，而不是可查事实。

拷问层级和必须追问的细节：

| 层级 | 必须拷问的细节 | 闭合证据 |
|---|---|---|
| 整体目标 | 用户为什么要做、目标对象是谁、失败现状是什么、成功后外部世界有什么变化 | Goal / User And Scenario 可写成可验证表述 |
| 大类/规划轴 | 按业务价值、风险、模块、用户路径、技术债、交付阶段中的哪条轴规划 | Scope 的组织方式和优先级依据明确 |
| 范围切片 | 本轮做哪一片、不做哪一片、哪些边界变更必须重新确认 | Scope / Non-Goals 能阻止范围漂移 |
| 小项目/模块 | 每片涉及哪些模块、文件族、接口、数据、文档或流程 | Proposed Design 能映射到 plan 的 File Map |
| 行为细节 | 正常路径、错误/空状态、边界条件、兼容性、用户可见文案或输出 | Acceptance Criteria 有可观察行为和证据来源 |
| 实现约束 | 技术方案、依赖、验证命令、回滚、发布、迁移、权限或安全风险 | Constraints / Risks / Verification 可执行 |

每层只问一个最高影响问题，但必须持续追问到该层闭合。用户给出笼统回答时，不能立刻生成 spec；必须把笼统回答转成下一层的具体决策问题继续拷问。只有低风险、可逆且不影响 AC/风险/验证的细节可用 assumption，并写明依据。

每层闭合前必须完成三项检查：

- 上游依赖检查：本层问题依赖的上游决策已经是 decided / deferred / out_of_scope，不能依赖 open 分支。
- 横向分支检查：同层的主要替代路径、失败路径、验证路径和风险路径已处理。
- 下游影响检查：本层决策对 Scope、Non-Goals、AC、Risks、Verification、Plan File Map 的影响已写明。

技术方案进入 plan 前必须满足：

- 技术方案所属的上一层目标、范围、验收和风险取舍已闭合。
- 已问清方案要优化的主轴：速度、正确性、兼容、可维护、用户体验、成本、风险或回滚。
- 已列出至少一个被拒绝方案及拒绝原因。
- 已写入 Decision Trace 和 Alternatives Considered。

若无法证明这些条件，必须继续 brainstorming，不得进入 planning。

### Shared Understanding Gate

展示 spec 草稿前，必须先通过共享理解确认门：

- `unresolved_branches` 为空，或剩余项明确标为不影响本轮 AC/风险/验证的 assumption。
- Decision Trace 覆盖本轮会影响目标、范围、验收、风险和验证方式的分支。
- 每个关键技术方案都能追溯到用户决策或合法 assumption。
- agent 输出一段共享理解摘要，列出目标、范围、非目标、关键取舍、验证方式和风险。
- 用户明确确认共享理解成立后，才可把 spec 标为 Approved 或进入 planning。

用户只是回复“继续”“可以”“嗯”时，不得自动视为共享理解成立；必须能对应到共享理解摘要的确认。

## 单问题澄清规则

每次澄清回复只能有一个用户决策问题。禁止问卷式列出多个问题、多个“请确认”或多个待答空位。

执行方式：

- 同时存在多个未知项时，先查本地事实；仍不确定时，只问对 spec 方向影响最大的一个问题。
- 问题按宏观到细节推进：整体目标 → 大类/规划轴 → 范围切片 → 小项目/模块 → 行为细节 → 实现约束。
- 用户说“重新规划 / 整体规划 / 重构规划 / 从头梳理 / 重新设计”时，默认进入宏观规划澄清；第一问必须确认规划视角或大类划分，不得直接问已有项目的文件、类名、接口、页面细节。
- 每个问题必须带已知事实、当前层级、2-3 个选项、推荐选项和下一步。
- 如果事实不足以给选项，先继续读取文件、文档、git、日志或已有计划；不要把本可查的信息转嫁给用户。
- 只有问题属于用户独占事实（例如私有业务目标、账号/权限、不可从仓库或上下文推断的偏好）时，才允许不给参考选项；必须说明已查事实和无法形成选项的原因。
- 面向用户的问题标题必须自然直接，禁止把“只需要你拍板 1 个问题”作为固定标题。只有最后一个收口问题确实是剩余唯一阻塞点时，才可在正文中使用类似提醒。

模板：

```markdown
**已知事实**：[1-3 句]
**当前层级**：[整体目标 / 大类划分 / 范围切片 / 小项目 / 行为细节 / 实现约束]
**当前分支**：[current_branch；说明依赖哪个上游决策]
**请确认**：[一个决策问题]

**选项**：
1. [选项 A] -> [结果]
2. [选项 B] -> [结果]
3. [选项 C] -> [结果，可选]

**推荐**：[推荐选项]，因为 [理由]。
**为什么问你**：[说明这是用户决策，不是本地可查事实]
**下一步**：[选定后继续事实收集或下一层澄清]
```

## Spec 模板

```markdown
# [任务名] Spec

**Date:** YYYY-MM-DD
**Quality level:** mvp | polished | production
**Status:** Draft | Approved

## Goal
[一句话目标]

## Target
- target_id: [目标 ID]
- target_statement: [外部可观察目标]
- success_definition: [完成状态，必须映射到 AC 和最终验证]
- scope_denominator: [目标范围分母；出现全部/完整/100%时必须列出可计数单元]
- target_principles: [冲突取舍原则和禁止降级规则]
- quality_level: [mvp | polished | production]
- stop_or_loop_conditions: [失败、部分完成、需重澄清、计划修订的回路条件]

## User And Scenario
[谁在什么场景下为什么使用]

## Scope
- [包含行为]

## Non-Goals
- [明确排除行为]

## Proposed Design
[架构、流程、UI/API 行为、数据流或内容结构]

## Decision Trace
| 层级[layer] | 决策点[decision_point] | 选项摘要[options] | 用户决策[user_decision] | 对范围/验收/风险/验证的影响[impact] |
|---|---|---|---|---|
| 整体目标 | [问题] | [2-3 个选项] | [用户选择或 ASM-N] | [影响] |
| 大类/规划轴 | ... | ... | ... | ... |

## Grilling Summary
- 共享理解[shared_understanding]: true | false
- 未闭合分支[unresolved_branches]: [无 / 列出剩余分支及为什么不阻塞]
- 关键取舍[key_tradeoffs]: [关键取舍]
- 拒绝方向[rejected_paths]: [明确拒绝的方向]

## Design Tree Coverage
| 分支 ID[branch_id] | 分支[name] | 上游依赖[parent] | 层级[layer] | 状态[status] | 决策引用[decision_ref] | 阻塞项[blocks] |
|---|---|---|---|---|---|---|
| B1 | [分支名] | [root/B-N] | [层级] | decided/deferred/out_of_scope/open | [Decision Trace/ASM-N] | [B-N 或无] |

## Alternatives Considered
- [方案]: [取舍和接受/拒绝原因]

## Acceptance Criteria
| ID | 验收项 | 验证方式 |
|---|---|---|
| AC-1 | [可观察要求] | [功能级命令 / 样例 / 流程 / 文件渲染 / 人工审查证据] |
| AC-2 | ... | ... |

## Constraints
- [精确约束]

## Risks
- [风险和缓解]
```

## 阶段输出

输出 `SpecPacket`。字段以 `SKILL.md` 的结构化交接 Packet 为准；本阶段至少填入 spec 路径、目标、decision_trace、用户场景、scope、non-goals、acceptance criteria、constraints、risks、quality level、是否获得用户确认。

## 自检门禁

确认 spec ready 前：

- 搜索 `TBD`、`TODO`、`later`、`maybe`、`适当处理`、模糊验收。
- 每条验收标准必须有证据来源。
- 必须包含 `## Target`；target_statement、success_definition、scope_denominator、target_principles、quality_level 和 stop_or_loop_conditions 不得为空。
- 若目标含“全部 / 完整 / 100% / 迁移 / 覆盖”，scope_denominator 必须列出可计数单元和完成判定；否则继续拷问。
- target_principles 必须能解释计划拆解、取舍和验证优先级；不得只写“按最佳实践”。
- 必须包含 `## Decision Trace`；重任务、重新规划类任务或明显方案分叉任务不得为空。
- Decision Trace 必须按整体目标 → 大类/规划轴 → 范围切片 → 小项目/模块 → 行为细节 → 实现约束的顺序记录已闭合层级；若跳层，必须继续澄清。
- Decision Trace 必须记录拆解轴、拆解粒度和功能级验证口径；若计划会涉及评价模型，还必须记录评价对象、维度、尺度、阈值、证据来源和失败反例。
- 必须包含 `## Grilling Summary`，且 `shared_understanding` 必须为 true 才能标 Approved。
- 若 `unresolved_branches` 非空，必须说明为什么不影响本轮 AC、风险边界和验证方式；否则继续拷问。
- 必须包含 `## Design Tree Coverage`；不得存在 `open` 分支。deferred 分支必须有 owner、原因和后续触发条件。
- **AC 必须以 `AC-N` 形式 ID 化**，唯一不重复；ID 后续供 TaskResult.ac_coverage 与 VerificationReport.coverage 引用。
- 每条 AC 必须定义功能级验证方式。纯静态文档或低风险文字修正可使用文件存在或文本命中作为主要证据；其余情况不得以此作为主要证据，只能标 weak。
- 必填门禁不得标 `N/A`；按需补充项标 `N/A` 时必须写原因。
- 非目标必须能阻止明显范围漂移。
- spec 必须小到能被一个 plan 执行；否则拆分。
