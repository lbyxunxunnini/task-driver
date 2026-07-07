# Brainstorming Mode

需求澄清与 spec 阶段。用于 task-driver 开工前：事实收集、深度澄清、方案比较、明确范围/非目标/验收/质量层级，并产出 approved spec 与 SpecPacket。

把粗糙请求变成 approved spec。此阶段不得写实现代码，不得脚手架化方案，也不得直接输出最终实施计划。

## 必做清单

1. 读取当前事实：文件、文档、git 状态、日志、报错、已有 spec/plan、相关命令。
2. 判断任务是否过大；过大时先识别任务类型，再拆第一片。
   - 若用户目标是“重新规划 / 整体规划 / 重构规划 / 从头梳理 / 重新设计”，第一片必须是规划框架片：目标、大类、范围边界、优先级和验收产物，不得直接拆到实现细节。
   - 若用户目标是功能实现或 bugfix，第一片必须覆盖一个可验证的端到端用户价值或最小复现闭环，不得只拆内部技术步骤。
   - 拆第一片前必须说明为什么该片最能降低不确定性或交付风险。
3. 禁止问卷式连续提 1 个以上问题；每轮只问一个最高影响决策点，直到决策树闭合。
4. 多方案时给出 2-3 个方案、取舍和推荐；禁止只抛开放问题。
5. 展示 spec，并取得用户确认。
6. 保存 approved spec：`docs/task-driver/specs/YYYY-MM-DD--slug.md`。
7. 按 `SKILL.md` 的 packet contract 输出 SpecPacket。
   - 如果 ledger 已存在，必须写入 ledger。
   - 如果 ledger 尚未创建，必须写入 spec 末尾的 `## SpecPacket` 或 planning handoff，并在 planning 创建 ledger 时同步复制。
   - 禁止只把 SpecPacket 留在对话记忆或未持久化草稿中。
   - planning 阶段创建 ledger 前必须检查 SpecPacket 是否已持久化；未持久化不得进入 plan 编写。
8. 自检 spec：无占位、矛盾、模糊验收、范围漂移。

## 澄清标准

按主控的“澄清分层”和“品质层级”执行。必填门禁必须闭合；按需补充项只有经事实收集和影响判断确认不影响方案或验收时，才可标 `N/A`，并必须写明判断依据；否则必须补齐。

必填门禁：

- Why：用户真实场景和期望收益。
- What：核心交付物和 2-5 个关键行为。
- Success：具体验收标准和证据来源。
- Quality：MVP / 精打磨 / 生产级。
- Scope：包含内容和明确非目标。
- Constraints：技术、时间、安全、合规、平台、风格、依赖限制。

按需补充：

- User：使用者和能力水平。
- Trade-offs：可裁剪项和不可裁剪项。
- Risks：风险和缓解。

只问会改变 spec 或决定 spec 生成路径的问题。对重新规划、整体规划、重构规划、从头梳理、重新设计类任务，规划视角、大类划分、范围切片和优先级都属于 spec 生成路径问题，必须按单问题澄清规则逐层闭合。能给参考答案时，必须给 2-3 个互斥选项和推荐答案，帮助用户决策；禁止借口“不能给参考答案”退回开放式提问。

技术方案选项也必须服从澄清层级。若方案会改变接口、数据模型、依赖、文件边界、验证方式、回滚方式、用户流程或风险边界，它不是 plan 细节，而是 spec 生成路径的一部分；必须停留在 brainstorming，通过单问题澄清逐层闭合。不得在目标、范围、验收、风险和取舍轴尚未闭合时，把技术方案拆成任务并进入 executing。

## 拷问细化协议

本阶段必须建立决策轨迹[Decision Trace]。它记录从宏观到细节的拷问链，证明 agent 不是跳到技术方案或任务拆解，而是和用户逐层达成一致。

### Grilling State

数据收集不是一次性表格填写，而是一个交互状态机。进入 brainstorming 后，必须在对话或 ledger 中维护当前数据收集状态。

**面向用户展示格式**（富文本摘要）：

```markdown
---
**数据收集[grilling_state]**

| 字段 | 当前值 |
|---|---|
| 当前分支[current_branch] | 整体目标 |
| 当前问题[current_question] | 确认解决问题的优先级和约束 |
| 已闭合决策[upstream_decisions] | 无 / [just_audio 可用性已确认] |
| 依赖关系[dependency] | 无 / 整体目标已闭合 |
| 推荐答案[recommended_answer] | 选项 1（用 just_audio 替代） |
| 用户决策[user_decision] | 待处理[pending] / 选项 1（已确认） |
| 未闭合分支[unresolved_branches] | [整体目标, 范围切片, 技术方案] |
| 共享理解[shared_understanding] | 否[false] |
---
```

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
- 行为分支：正常路径、错误路径、空状态、边界条件。
- 方案分支：关键技术方案、替代方案、拒绝理由。
- 验证分支：自动验证、人工验收、证据强度上限。
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
| AC-1 | [可观察要求] | [命令 / 文件 / 交互证据] |
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
- 必须包含 `## Target`；target_statement、success_definition、quality_level 和 stop_or_loop_conditions 不得为空。
- 必须包含 `## Decision Trace`；重任务、重新规划类任务或明显方案分叉任务不得为空。
- Decision Trace 必须按整体目标 → 大类/规划轴 → 范围切片 → 小项目/模块 → 行为细节 → 实现约束的顺序记录已闭合层级；若跳层，必须继续澄清。
- 必须包含 `## Grilling Summary`，且 `shared_understanding` 必须为 true 才能标 Approved。
- 若 `unresolved_branches` 非空，必须说明为什么不影响本轮 AC、风险边界和验证方式；否则继续拷问。
- 必须包含 `## Design Tree Coverage`；不得存在 `open` 分支。deferred 分支必须有 owner、原因和后续触发条件。
- **AC 必须以 `AC-N` 形式 ID 化**，唯一不重复；ID 后续供 TaskResult.ac_coverage 与 VerificationReport.coverage 引用。
- 必填门禁不得标 `N/A`；按需补充项标 `N/A` 时必须写原因。
- 非目标必须能阻止明显范围漂移。
- spec 必须小到能被一个 plan 执行；否则拆分。
