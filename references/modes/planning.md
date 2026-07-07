# Planning Mode

计划阶段。用于 approved spec 之后、执行之前：创建实施 plan、文件映射、接口、任务拆解、TDD/验证命令、review gate、ledger 和 PlanPacket。

写出一个新 agent 也能执行的计划。Plan 是执行契约；确认后不应再靠连续追问推进。

## 必要输入

- Approved spec，可内联输入或位于 `docs/task-driver/specs/`；进入 plan 编写前，SpecPacket 必须已持久化到 ledger、spec `## SpecPacket` 或 planning handoff。
- Approved spec 必须包含决策轨迹[Decision Trace]、拷问摘要[Grilling Summary] 和设计树覆盖[Design Tree Coverage]。重任务、重新规划类任务或明显方案分叉任务若缺少 Decision Trace，或轨迹没有从宏观到细节闭合，或 `shared_understanding` 不是 true，或 Design Tree Coverage 存在 open 分支，不得进入 plan 编写。
- Approved spec 必须包含目标定义[Target] 或等价字段：target_id、target_statement、success_definition、quality_level、stop_or_loop_conditions。缺失时回到 brainstorming。
- 当前项目事实必须先收集到足以支撑 plan，不得只读目录结构。至少检查：
  - 项目规则：CLAUDE.md、README、CONTRIBUTING、docs、.claude/、agent 规则文件。
  - 代码结构：入口、模块/页面/服务边界、路由、配置、平台目录。
  - 依赖与脚本：package/pubspec/build 配置、测试/lint/analyze/build 命令。
  - 现有任务资产：已有 spec/plan/ledger、TODO、issue 记录、错误记录、工作清单。
  - git 状态：当前分支、未提交改动、主分支风险。
  - 当前行为或失败证据：日志、报错、复现路径、已有验证结果。
- 用户约束和质量层级。
- 主控定义的重任务判定、明显方案分叉、品质层级和执行-验证循环退出规则。

缺少且本地无法查到的信息，不得直接进入计划编写。

处理顺序：

1. 先判断缺口属于哪类：用户决策 / 外部权限或凭据 / spec 缺口 / 项目事实缺口 / plan 细节缺口。
2. 项目事实缺口：继续读取文件、文档、配置、日志或运行只读诊断命令，不得转嫁给用户。
3. spec 缺口：回到 brainstorming，用单问题澄清门补齐。
4. 用户决策或外部权限/凭据：用单问题澄清门回问。
5. plan 细节缺口：若不改变 spec、AC、范围和风险边界，可在 plan 中提出明确 assumption；否则回到 brainstorming 或停机回问。

若缺口是技术方案选项，先判断它是否改变接口、数据模型、依赖、文件边界、验证方式、回滚方式、用户流程、风险边界或交付范围。会改变任一项时，它属于 spec 决策，必须回到 brainstorming；只有纯实现顺序、局部代码组织、命名或同等风险的微小取舍，才可作为 plan assumption 或任务细节处理。

计划中的每个技术任务都必须能追溯到 Decision Trace、Acceptance Criteria 或 Constraints。若一个任务本质是“选择技术方案”“调研后决定路线”“看情况实现 A/B”，说明拷问没有闭合，必须回到 brainstorming；plan 只能执行已确认方案，不能继续替用户做方案决策。

planning 阶段只负责把已确认的目标和方案拆成可执行契约。若发现目标、范围、非目标、AC、质量层级、技术取舍、风险边界、共享理解或验收方式任一项未闭合，必须回到 brainstorming；不得在 plan 中自行补默认值。

Plan assumption 必须包含：

- assumption_id：`ASM-N`
- 内容：具体假设，不得使用“大概 / 应该 / 常规”。
- 依据：来自哪些文件、命令、日志或文档。
- 验证点：在哪个任务或命令中验证该假设。
- 失效处理：假设不成立时进入 blocked / plan-revision / brainstorming 的哪一路。
- 影响范围：该假设影响哪些 T-NNN / AC-N。

执行阶段一旦发现 assumption 不成立，必须停止当前任务并按失效处理路由，不得继续执行。

任何回问都必须遵守单问题澄清门，不得一次列多个 planning 问题。

## Plan 要求

保存到 `docs/task-driver/plans/YYYY-MM-DD--slug.md`。

必须包含：

- target_id、目标和 spec 路径。
- 目标达成定义：用 1-3 句说明完成后什么外部行为、文档状态、质量状态或可观察结果成立；不得只有任务列表。
- 验证方案摘要：在任务清单前先说明最终要运行/检查的验证类型、覆盖哪些 AC、证据强度上限和无法自动验证的人工证据。
- 从 spec 复制的全局约束。
- 门禁模式：`strict`、`standard` 或 `lite`，写入 `PlanPacket.gate_mode`。
- 执行模式：`single-agent`、`multi-agent-review` 或 `multi-agent-parallel`，写入 `PlanPacket.execution_mode`。
- 品质层级对应的验收差异。
- 文件映射：创建/修改/测试/文档路径及职责。
- 接口：函数、命令、配置键、schema 或公开行为。
- 任务拆分：每个任务能独立验证和评审。
- 行为变化：TDD 步骤、预期失败、最小实现、通过命令、重构边界。
- 非代码变化：确定性的验证步骤。
- 每个任务的 review gate。
- ledger 路径：`docs/task-driver/ledgers/`。
- 每个任务需要消费和产出的 packet；字段以 `SKILL.md` 的 packet contract 为准。
- 停机条件和回滚说明。
- 同一 requirement 最多 2 轮执行-验证循环；超过后进入 `blocked`、`partial` 或 `plan-revision`。

## 禁止占位

这些都是 plan 失败：

- `TBD`、`TODO`、`later`、`etc.`
- “适当处理校验”但没有精确校验规则。
- “写测试”但没有测试文件、测试名、行为和命令。
- “实现逻辑”但没有具体行为。
- 引用未定义的函数、文件、命令或配置键。
- “类似上一步”而不重复必要细节。

反例：

- `实现用户管理逻辑`：失败，缺文件、行为、测试和验收。
- `补充必要测试`：失败，缺测试文件、测试名和命令。
- `处理异常情况`：失败，缺异常类型和期望行为。
- `按前面方式完成剩余模块`：失败，缺逐项任务定义。

## Plan 模板

```markdown
# [任务名] Implementation Plan

**Spec:** docs/task-driver/specs/YYYY-MM-DD--slug.md
**Ledger:** docs/task-driver/ledgers/YYYY-MM-DD--slug.md
**Gate mode:** strict | standard | lite
**Execution mode:** single-agent | multi-agent-review | multi-agent-parallel
**Quality level:** mvp | polished | production
**Status:** Draft | Approved
**Plan version:** v1
**Predecessor:** 无（首版） | docs/task-driver/plans/YYYY-MM-DD--slug.md（v[N-1] 路径）

## Goal
[一句话目标]

## Target
- target_id: [目标 ID]
- target_statement: [外部可观察目标]
- success_definition: [完成状态]
- quality_level: [mvp | polished | production]
- stop_or_loop_conditions: [回路条件]

## Success Definition
- [目标达成后的可观察结果，对应 AC-N]

## Verification Strategy
- [最终验证类型、命令或检查方式、覆盖 AC-N、预期 evidence_strength]

## Global Constraints
- [精确约束]

## File Map
- Create: `path` - [职责]
- Modify: `path` - [职责]
- Test: `path` - [职责]

## Interfaces
- [名称/签名/命令/schema 和消费者]

## Tasks

### Task T-001: [名称]
**Owner role:** Implementer
**Files:** [精确路径]
**Acceptance:** [引用 spec 的 AC-N 列表]
**Review gate:** spec compliance + code/content quality

- [ ] Step 1: 在 `path` 写 [行为] 的失败测试。
      Run: `[command]`
      Expected: 因为 [缺失行为] 失败。
- [ ] Step 2: 在 `path` 做最小实现。
- [ ] Step 3: 运行 `[command]`。
      Expected: 通过。
- [ ] Step 4: 写 TaskResult packet 到 ledger。
- [ ] Step 5: 写 ReviewReport packet 到 ledger。

## Verification Plan
- [最终命令、预期结果、覆盖的 AC-N 列表、预期 evidence_strength]

## Stop Conditions
- [必须暂停回问的情况]

## Diff From v[N-1]
仅 plan v2 及以上版本必填。首版（v1）可省略本段。

但如果 v1 是对已有计划、旧实现、历史文档或现有流程的“重新规划 / 重构规划 / 替代方案”，必须新增 `## Change From Current State`，说明相对当前状态的结构性变化、保留项、废弃项和迁移风险。
- [结构性差异简述：新增/删除/重排的任务 ID、接口变更、File Map 变更]
```

## Plan Revision Protocol

触发条件：执行-验证循环 2 轮仍失败、或执行中发现 plan 假设错误（接口、依赖、范围）。

判定：

只能在以下条件全部满足时，判定为 “spec 仍正确，仅升级 plan”：

- Goal 不变。
- Scope / Non-goals 不变。
- Acceptance Criteria 不变，或只补充验证方式但不改变验收语义。
- Constraints 不变。
- Quality level 不变。
- 风险边界不扩大。
- 失败原因来自实现路径、任务顺序、文件映射、接口假设、依赖假设或验证命令设计。

出现任一情况，必须判定为 “spec 也错误”，回到 brainstorming：

- 用户目标或真实场景变化。
- Scope / Non-goals 需要增删。
- AC 需要新增、删除、降级、改语义。
- Constraints 或 Quality level 需要变化。
- 继续执行会扩大风险边界、权限、安全、迁移、发布或数据影响。
- 原 spec 的 Proposed Design 已经误导 plan。

操作：

- **spec 仍正确**：仅升级 plan。`plan_version` 递增（v1 → v2），`predecessor` 指向前版路径，新 plan 必须填写 `## Diff From v[N-1]`。前版 PlanPacket.status 置 `superseded`。
- **spec 也错误**：回到 brainstorming 重写 spec，旧 SpecPacket.status 置 `superseded`，再产出新 plan v1。
- 新 plan 必须获得用户 approve；approve 前禁止继续执行。
- ledger 不重建；Decisions 段记录本次 plan-revision 原因、时间、v号跳转。

## Ledger 模板

执行前创建：

```markdown
# [任务名] Progress Ledger

**Spec:** docs/task-driver/specs/YYYY-MM-DD--slug.md
**Plan:** docs/task-driver/plans/YYYY-MM-DD--slug.md
**Gate mode:** strict | standard | lite
**Execution mode:** single-agent | multi-agent-review | multi-agent-parallel
**Started:** YYYY-MM-DD

## Status
- T-001: pending

## Packets
- SpecPacket: [path or inline summary]、status
- PlanPacket: [path]、plan_version、gate_mode、execution_mode、status
- TaskResult: pending
- ReviewReport: pending
- VerificationReport: pending

## Iteration Log
每轮执行-验证循环写一条，最多 2 轮。
- attempt: 1
  requirement_id: AC-N | T-NNN
  hypothesis: [本轮假设]
  command: [运行的命令]
  result: [结果摘要 + exit_code]
  next_assumption: [下轮假设或退出]
  outcome: pass | fail | blocked | partial | plan-revision

## Evidence
结构化证据条目；每条一个列表项。
- timestamp: 2026-06-23T10:00:00
  command: `pytest tests/test_x.py::test_y`
  exit_code: 0
  output_excerpt: "1 passed in 0.42s"
  covers_requirement_ids: [AC-1, AC-2]
  strength: strong | medium | weak | stale

## Review Findings
- T-NNN: severity / file / issue / required_fix / status

## Decisions
- [timestamp] / [source] / [decision]
```

## 阶段输出

输出 `PlanPacket` 并创建 ledger。字段以 `SKILL.md` 的结构化交接 Packet 为准；本阶段至少填入 plan 路径、ledger 路径、门禁模式、执行模式、任务 id、owner role、objective、files、steps、verification、stop conditions。

## 自检门禁

交给用户确认前：

- 检查 SpecPacket 是否已持久化；若只存在于 spec 的 `## SpecPacket` 或 planning handoff，创建 ledger 时必须同步复制；未持久化不得进入 plan 编写。
- 检查 spec 的 Decision Trace 是否存在、按层级闭合，并能解释技术方案、范围切片和验证策略来源。
- 检查 spec 的 Grilling Summary：`shared_understanding` 必须为 true；`unresolved_branches` 非空时必须证明不影响本轮 AC、风险边界和验证方式。
- 检查 spec 的 Design Tree Coverage：目标、范围、行为、方案、验证、风险分支必须覆盖；不得存在 open 分支。
- 检查 Target 是否存在并贯穿 plan；每个任务和验证项必须能映射到 target_id、AC 或 stop_or_loop_conditions。
- 每条 spec AC-N 必须映射到任务或验证命令；映射以 AC ID 引用。
- `## Goal`、`## Success Definition` 和 `## Verification Strategy` 必须先于任务清单出现，且不能与任务步骤重复成同义列表。
- 搜索占位词。
- 检查任务顺序、接口名称、路径一致。
- 检查 ledger 路径存在于 plan。
- 一次性请求完整 plan 确认；确认后执行阶段不逐步讨确认。
- **PlanPacket 单源校验**：plan markdown 任务条目（`### Task T-NNN`）必须与 PlanPacket.tasks[] 一一对应，字段 id / files / acceptance / verification 完全一致；漂移以 packet 为准，立即同步 markdown。
- 检查 plan-revision 字段：v1 可省 `## Diff From v[N-1]`；v2+ 必填、`predecessor` 指向前版；重新规划类 v1 必须含 `## Change From Current State`。
- 检查是否仍存在未闭合的技术方案分叉；若存在，回到 brainstorming，不得让用户 approve plan 后再边做边决定。
