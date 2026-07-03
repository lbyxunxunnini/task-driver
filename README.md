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
    glossary.md
    packet-contract.md
    runtime-protocols.md
    quality-rubric.md
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

1. **brainstorming**：先查项目、文件、git、日志和已有文档；深度澄清 Why、scope、success、quality、constraints；产出 approved spec 和 SpecPacket。
2. **planning**：保存 plan，包含文件映射、接口、任务、TDD/验证命令、Review Gate、停机条件和 PlanPacket。
3. **executing**：确认后连续推进，行为变化优先 TDD；每个任务写 TaskResult 和 ReviewReport，更新 ledger。
4. **verification**：最终对照验收标准运行 fresh verification，输出 VerificationReport 和用户验收状态。

阶段参考文档位于 `references/modes/`。这些文件不是独立 skill，只是根控制器的内部协议补充。

长协议已拆到 `references/`，根 `SKILL.md` 只保留入口、硬门禁和读取索引：

- `references/glossary.md`：中文显示名和术语表。
- `references/packet-contract.md`：Packet schema、状态机、跨引用、证据强度。
- `references/runtime-protocols.md`：Red Flags、TDD 例外、循环退出、Plan Revision、User Acceptance Gate。
- `references/quality-rubric.md`：verification 阶段的 1-5 质量评分、阈值和 improve loop。
- `references/error-templates.md`：停机、验证失败、循环退出、范围漂移、阻塞模板。

根 `SKILL.md` 按 P0/P1/P2 读取优先级加载引用文件，避免每次任务读取全部 references。

## 最短流程

```text
tdr- 帮我把这个 bug 从定位到验证完整跑完
```

触发后，Task Driver 会按以下顺序推进：

1. 收集项目事实，先读相关文件、文档、git 状态、日志或失败证据。
2. 若目标、范围、验收或质量层级不清楚，只问一个最高影响决策点，并给出选项和推荐。
3. 生成或内联 approved spec，写清 Goal、Scope、Non-goals、Acceptance Criteria、Constraints、Quality Level。
4. 生成 approved plan 和 ledger，明确文件映射、任务、验证命令、Review Gate 和停机条件。
5. 按 plan 连续执行，写 TaskResult 和 ReviewReport，最后运行 fresh verification；需要时按质量层级输出 `quality_score`。

## 工件

- Spec：`docs/task-driver/specs/YYYY-MM-DD--slug.md`
- Plan：`docs/task-driver/plans/YYYY-MM-DD--slug.md`
- Ledger：`docs/task-driver/ledgers/YYYY-MM-DD--slug.md`

在本仓库中，`docs/task-driver/` 是运行时生成的 spec/plan/ledger 目录，建议通过 `.gitignore` 忽略。

## 治理门禁

- **重任务判定**：跨 2 个以上文件/模块，或目标、范围、验收、质量层级不清楚，或涉及数据、权限、安全、发布、迁移、外部服务、破坏性操作时，必须走 Task Driver。
- **执行模式**：`strict[严格]`（高风险/生产级）、`standard[标准]`（默认）、`lite[轻量]`（中等任务门禁放宽）。详见 SKILL.md。
- **明显方案分叉**：会改变 API、数据模型、用户流程、依赖、验证方式、风险边界、交付范围或回滚方式的选择，必须在 spec/plan 阶段确认。
- **澄清分层**：Goal、Scope、Non-goals、Acceptance Criteria、Constraints、Quality Level 是必填门禁；User scenario、Risks、Trade-offs、Alternatives 按需补充。
- **单问题澄清**：禁止问卷式连续提 1 个以上问题；每轮只问一个最高影响决策点，能给参考答案时必须给 2-3 个互斥选项和推荐。
- **重新规划顺序**：重新规划、整体规划、重构规划、从头梳理或重新设计类任务，必须先从整体规划视角或大类划分开始，再进入小项目和细节。
- **品质层级**：MVP 覆盖核心路径；精打磨覆盖主要边界和错误状态；生产级覆盖安全、权限、性能、兼容、观测、回滚/迁移和完整回归。
- **断点续传**：中断后重新触发时，agent 读取 ledger 的 Resume Checkpoint 判定是否可续传；可恢复错误自动重试 1 次。详见 `references/resume-protocol.md`。
- **执行-验证循环**：同一 requirement 最多 2 轮；仍失败则进入 `blocked`、`partial` 或 `plan-revision`。
- **证据强度**：`strong` 才能标 `Met`；`medium` 最多 `Partial`；`weak` / `stale` 必须 `Not met` 或 `Blocked`。
- **质量评分**：verification 阶段按质量层级判断是否输出 `quality_score`；低于阈值时回到 executing、plan-revision、brainstorming 或 blocked。
- **中文显示名**：用户可见输出优先使用中文显示名；首次出现英文协议标识时采用”中文显示名（英文标识）”，字段名、枚举值、路径、JSON/YAML key 等机器契约保持原值。

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

## 当前状态

当前版本：v0.6.1

v0.6.1 新增分级执行模式（strict / standard / lite）、断点续传与自动恢复协议、端到端使用案例（walkthrough）、FAQ，以及错误自分类与自动重试机制。
