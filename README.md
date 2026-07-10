# Task Driver

Task Driver 是面向 agent 重任务的单 skill 多阶段工作流包。目标是把一个任务从“模糊请求”推进到“可验证交付”：事实收集、深度澄清、spec、plan、连续执行、TDD/评审、verification。

它的重点不是替 agent 写更多提示词，而是建立可恢复、可验证、可降级的执行协议。

## 能力边界

Task Driver 负责流程治理，不替代具体领域 skill。它解决的问题是：

- 模糊任务开工前问不透。
- 计划太粗，执行中频繁回问。
- 长任务上下文压缩后丢进度。
- 没有 spec/plan/ledger，完成标准不可追踪。
- 没有 fresh verification evidence 就口头宣布完成。

不追求：

- 强制所有任务都走重流程。
- 替代语言、框架、UI、数据库等领域专用 skill。

## 使用方式

触发规则：用户消息以 `tdr-`、`task-driver` 或 `/task-driver` 开头时，应进入 Task Driver。

示例：

```text
tdr- 帮我把这个功能从需求澄清到实现验证完整跑完
```

或：

```text
task-driver 根据这个 bug 先查根因，再做计划和修复
```

也可以使用：

```text
/task-driver 先把这个重构任务拆成 spec 和 plan
```

## 安装方式

Task Driver 现在只保留单 skill 多阶段模式，结构与 `flutter-forge` 类似：宿主只需要安装仓库根目录，运行时只暴露一个 `task-driver` skill。

```text
task-driver/
  SKILL.md
  .skillhub.json
  VERSION
  references/
    quick-start.md
    glossary.json
    packet-contract.md
    packet-templates.md
    runtime-protocols.md
    quality-rubric.md
    self-test-checklist.md
    error-templates.md
    resume-protocol.md
    walkthrough.md
    faq.md
    modes/
      brainstorming.md
      planning.md
      executing.md
      verification.md
    counterexamples/
      brainstorming.md
      planning.md
      executing.md
      verification.md
    walkthroughs/
      lite.md
      standard.md
      strict.md
  scripts/
    check-contracts.sh
```

ccswitch / SkillHub / Claude / Codex 这类传统 skill 搜索路径都应安装整个目录：

```bash
cp -R task-driver ~/.cc-switch/skills/task-driver
```

或：

```bash
cp -R task-driver ~/.claude/skills/task-driver
```

安装后只应该看到一个入口：

```text
task-driver
```

不再暴露 `task-driver-standalone`，也不再暴露 `task-driver-brainstorming`、`task-driver-planning`、`task-driver-executing`、`task-driver-verification` 四个子 skill。

## 工作流

根 `SKILL.md` 是唯一控制器。内部按以下阶段模式推进：

1. **需求澄清阶段[brainstorming]**：先查项目、文件、git、日志和已有文档；深度澄清目的[Why]、范围分母[scope_denominator]、目标原则[target_principles]、成功标准[success]、质量要求[quality]、约束[constraints]；产出已确认需求规格[approved spec]和需求规格交接包[SpecPacket]。
2. **计划阶段[planning]**：保存计划[plan]，包含目标覆盖矩阵[Target Coverage Matrix]、拆解策略[Decomposition Strategy]、文件映射[File Map]、接口、任务、功能级验证、评审门禁[Review Gate]、停机条件和计划交接包[PlanPacket]。
3. **执行阶段[executing]**：确认后连续推进，行为变化优先 TDD；每个任务写任务结果[TaskResult]和评审报告[ReviewReport]，更新执行台账[ledger]，不得静默降低目标。
4. **验证阶段[verification]**：最终对照验收标准和目标覆盖矩阵运行新鲜功能级验证证据[fresh functional evidence]，输出验证报告[VerificationReport]和用户验收状态。

阶段参考文档位于 `references/modes/`。这些文件不是独立 skill，只是根控制器的内部协议补充。

长协议已拆到 `references/`，根 `SKILL.md` 只保留入口、硬门禁和读取索引：

- `references/quick-start.md`：30 秒使用判断、门禁模式选择和最终交付最低要求。
- `references/glossary.json`：中文显示名和术语表。
- `references/packet-contract.md`：Packet schema、状态机、跨引用、证据强度。
- `references/packet-templates.md`：5 类 packet 的最小合法 YAML 模板。
- `references/runtime-protocols.md`：Red Flags、TDD 例外、循环退出、Plan Revision、User Acceptance Gate。
- `references/quality-rubric.md`：verification 阶段的 1-5 质量评分、阈值和 improve loop。
- `references/self-test-checklist.md`：发布前自测清单和一致性验证命令。
- `references/error-templates.md`：停机、验证失败、循环退出、范围漂移、阻塞模板。
- `references/walkthroughs/`：lite、standard、strict 三条黄金路径。

根 `SKILL.md` 按 P0/P1/P2 读取优先级加载引用文件，避免每次任务读取全部 references。`references/glossary.json` 是用户可见输出的启动级必读文件：首次说明阶段、协议、状态、字段或模式前必须读取。

## 最短流程

```text
tdr- 帮我把这个 bug 从定位到验证完整跑完
```

触发后，Task Driver 会按以下顺序推进：

1. 收集项目事实，先读相关文件、文档、git 状态、日志或失败证据。
2. 若目标、范围、验收或质量层级不清楚，只问一个最高影响决策点，并维护 Grilling State；默认只向用户展示当前决策摘要，完整状态写入 ledger。
3. 通过 Shared Understanding Gate 后，生成或内联 approved spec，写清 Goal、Target、scope_denominator、target_principles、Decision Trace、Grilling Summary、Scope、Non-goals、Acceptance Criteria、Constraints、Quality Level。
4. 生成 approved plan 和 ledger，明确目标达成定义、目标覆盖矩阵、拆解策略、验证策略、文件映射、任务、功能级验证命令、Review Gate 和停机条件。
5. 按 plan 连续执行整个 PlanPacket，写 TaskResult 和 ReviewReport，最后运行 fresh functional verification；需要时按质量层级输出 `quality_score`，并在请求用户验收前完成自检优化循环。

## 30 秒选择

需要快速判断时，先读 `references/quick-start.md`：

- 单文件低风险、有确定性验证：`gate_mode: lite`。
- 跨 2-5 文件、默认风险：`gate_mode: standard`。
- 安全、权限、数据、发布、迁移、公共 API 或生产级：`gate_mode: strict`。

示例路径：

- `references/walkthroughs/lite.md`
- `references/walkthroughs/standard.md`
- `references/walkthroughs/strict.md`

## 工件

- Spec：`.task-driver/specs/YYYYMMDD-HHmm-主题.md`
- Plan：`.task-driver/plans/YYYYMMDD-HHmm-主题.md`
- Ledger：`.task-driver/ledgers/YYYYMMDD-HHmm-主题.md`

在本仓库中，`.task-driver/` 是运行时生成的 spec/plan/ledger 目录，必须通过 `.gitignore` 忽略。

## 治理门禁

- **重任务判定**：跨 2 个以上文件/模块，或目标、范围、验收、质量层级不清楚，或涉及数据、权限、安全、发布、迁移、外部服务、破坏性操作时，必须走 Task Driver。
- **目标驱动状态机**：每个任务必须有 `Target`，包含 target_id、目标陈述、范围分母、目标原则、完成定义、质量层级和回路条件；正常状态链为 Target → brainstorming → planning → executing → verification → User Acceptance Gate → accepted_by_user。
- **精准目标门禁**：目标出现“全部 / 完整 / 100% / 迁移 / 覆盖”时，必须先定义可计数分母；没有分母不得进入 planning。
- **拆解深度门禁**：计划不能只列 Phase、文件或产物名，必须写明拆解轴、拆解层级、每层产物、每层验收和任务粒度下限。
- **目标覆盖矩阵**：scope_denominator 中每个目标单元必须映射到 T-NNN 和验证项；未覆盖目标单元是 Critical 缺口。
- **跳过记录**：brainstorming、planning、executing、verification、User Acceptance Gate 正常都必须出现；跳过必须记录 skipped_stage、reason、risk、replacement_evidence 和 user_approval。
- **门禁模式**：`strict[严格]`（高风险/生产级）、`standard[标准]`（默认）、`lite[轻量]`（中等任务门禁放宽），写入 `PlanPacket.gate_mode`。agent 执行形态另写入 `PlanPacket.execution_mode`。
- **明显方案分叉**：会改变 API、数据模型、用户流程、依赖、验证方式、风险边界、交付范围或回滚方式的选择，必须在 spec/plan 阶段确认。
- **澄清分层**：Goal、Scope、Non-goals、Acceptance Criteria、Constraints、Quality Level 是必填门禁；User scenario、Risks、Trade-offs、Alternatives 按需补充。
- **单问题澄清**：禁止问卷式连续提 1 个以上问题；每轮只问一个最高影响决策点，能给参考答案时必须给 2-3 个互斥选项和推荐。
- **自然澄清话术**：单问题是决策结构，不是固定话术；不得反复使用“只需要你拍板 1 个问题”这类标题，除非已经是最终收口问题。
- **技术方案闭合**：会改变接口、依赖、验证方式、回滚方式、用户流程或风险边界的技术方案，必须先在需求澄清阶段[brainstorming]确认取舍轴和方案选择。
- **拷问细化协议**：澄清必须按整体目标 → 大类/规划轴 → 范围切片 → 小项目/模块 → 行为细节 → 实现约束推进；每层要说明排除项、AC 影响、风险边界和验证影响。
- **Grilling State**：拷问必须维护当前分支、当前唯一问题、上游依赖、推荐答案、用户决策和未闭合分支；默认面向用户展示决策摘要，完整状态写入 ledger，不得最后补表伪造过程。
- **Design Tree Coverage**：拷问必须覆盖目标、范围、行为、方案、验证、风险分支；任何 open 分支都会阻止进入 planning。
- **事实与决策分离**：代码、文档、日志、git 和已有工件能查到的事实由 agent 自查；目标、优先级、范围、风险、质量和方案取舍由用户决策。
- **Decision Trace / Grilling Summary**：重任务、重新规划类任务或明显方案分叉任务的 spec 必须记录决策轨迹和共享理解摘要；计划里的技术任务必须能追溯到该轨迹、AC 或 Constraints。
- **Shared Understanding Gate**：用户明确确认共享理解前，不得把 spec 标为 Approved，不得进入 planning。
- **计划目标与验证策略**：计划阶段[planning] 必须先写目标达成定义和验证策略，再拆任务，避免只推进小任务而无法判断整体完成。
- **整体计划推进**：用户确认计划后，执行阶段[executing] 必须连续推进整个 PlanPacket；阶段、批次、小目标或单个任务完成不是“是否继续”的停机点。
- **回路规则**：planning / executing 发现未澄清目标、范围、AC、技术取舍或风险边界时必须回到 brainstorming；verification 根据失败性质回到 executing、planning 或 brainstorming。
- **验收前自检**：进入用户验收门禁[User Acceptance Gate] 前，必须逐项自检任务结果、评审报告、AC 覆盖、目标覆盖、验证策略、范围漂移、质量门、残余风险和自检优化循环；没有自检表不得询问用户是否接受。
- **重新规划顺序**：重新规划、整体规划、重构规划、从头梳理或重新设计类任务，必须先从整体规划视角或大类划分开始，再进入小项目和细节。
- **品质层级**：机器枚举统一为 `mvp` / `polished` / `production`；用户可见显示为 MVP / 精打磨 / 生产级。MVP 覆盖核心路径；精打磨覆盖主要边界和错误状态；生产级覆盖安全、权限、性能、兼容、观测、回滚/迁移和完整回归。
- **断点续传**：中断后重新触发时，agent 读取 ledger 的 Resume Checkpoint 判定是否可续传；可恢复错误自动重试 1 次。详见 `references/resume-protocol.md`。
- **执行-验证循环**：同一 requirement 最多 2 轮；仍失败则进入 `blocked`、`partial` 或 `plan-revision`。
- **证据强度**：强证据[`strong`] 必须优先来自功能级验证；中等证据[`medium`] 最多部分完成[`Partial`]；文件存在、文本命中、只看 diff 或弱证据[`weak`] / 过期证据[`stale`] 必须标未满足[`Not met`] 或受阻[`Blocked`]。
- **禁止静默降级**：目标范围内未覆盖项不得进入普通 backlog；必须修复、受阻、计划修订或由用户明确批准降级。
- **质量评分**：验证阶段[verification] 按质量层级判断是否输出 `quality_score`；低于阈值时回到执行阶段[executing]、计划修订协议[plan-revision]、需求澄清阶段[brainstorming]或受阻[blocked]。
- **中文显示名**：用户可见输出优先使用中文显示名；首次出现英文协议标识时采用 `中文显示名[英文标识]`，字段名、枚举值、路径、JSON/YAML key 等机器契约保持原值。中间进度更新、阶段切换说明、停机回问、最终报告都受该规则约束。

## 多 Agent 与降级

Task Driver 支持多 agent，但不依赖多 agent。

- 有 subagent/parallel agent 工具时，可以把 review、verification 或互不依赖的实现任务分派出去。
- 没有 subagent 能力时，自动使用 `single-agent`：同一个 agent 按 Brainstormer、Planner、Implementer、Reviewer、Verifier 顺序执行。
- 两种模式都必须使用同一套结构化交接 packet：`SpecPacket`、`PlanPacket`、`TaskResult`、`ReviewReport`、`VerificationReport`。
- 多 agent 输出只是证据，不是最终权威；controller 仍负责对照 spec/plan/ledger 做最终判断。

## 反例门禁

反例门禁限制 agent 把“看起来像完成”的状态误判为完成。各阶段反例独立维护，执行对应阶段前必须读取：

- `references/counterexamples/brainstorming.md`
- `references/counterexamples/planning.md`
- `references/counterexamples/executing.md`
- `references/counterexamples/verification.md`
- `references/counterexamples/global.md`

## 当前状态

当前版本：v0.8.1

v0.8.0 将产物目录统一为 `.task-driver/`，新增精准目标、拆解深度、功能级检验、反偷懒和自检优化循环门禁。

## 自测

发布前运行：

```bash
scripts/check-contracts.sh
git diff --check
```
