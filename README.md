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

直接触发：

```text
tdr- 帮我把这个功能从需求澄清到实现验证完整跑完
```

或：

```text
task-driver 根据这个 bug 先查根因，再做计划和修复
```

## 安装方式

Task Driver 现在只保留单 skill 多阶段模式，结构与 `flutter-forge` 类似：宿主只需要安装仓库根目录，运行时只暴露一个 `task-driver` skill。

```text
task-driver/
  SKILL.md
  .skillhub.json
  VERSION
  references/
    modes/
      brainstorming.md
      planning.md
      executing.md
      verification.md
  docs/
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

## 工件

- Spec：`docs/task-driver/specs/YYYY-MM-DD--slug.md`
- Plan：`docs/task-driver/plans/YYYY-MM-DD--slug.md`
- Ledger：`docs/task-driver/ledgers/YYYY-MM-DD--slug.md`

## 治理门禁

- **重任务判定**：跨 2 个以上文件/模块，或目标、范围、验收、质量层级不清楚，或涉及数据、权限、安全、发布、迁移、外部服务、破坏性操作时，必须走 Task Driver。
- **明显方案分叉**：会改变 API、数据模型、用户流程、依赖、验证方式、风险边界、交付范围或回滚方式的选择，必须在 spec/plan 阶段确认。
- **澄清分层**：Goal、Scope、Non-goals、Acceptance Criteria、Constraints、Quality Level 是必填门禁；User scenario、Risks、Trade-offs、Alternatives 按需补充。
- **单问题澄清**：禁止问卷式连续提 1 个以上问题；每轮只问一个最高影响决策点，能给参考答案时必须给 2-3 个互斥选项和推荐。
- **重新规划顺序**：重新规划、整体规划、重构规划、从头梳理或重新设计类任务，必须先从整体规划视角或大类划分开始，再进入小项目和细节。
- **品质层级**：MVP 覆盖核心路径；精打磨覆盖主要边界和错误状态；生产级覆盖安全、权限、性能、兼容、观测、回滚/迁移和完整回归。
- **执行-验证循环**：同一 requirement 最多 2 轮；仍失败则进入 `blocked`、`partial` 或 `plan-revision`。
- **证据强度**：`strong` 才能标 `Met`；`medium` 最多 `Partial`；`weak` / `stale` 必须 `Not met` 或 `Blocked`。
- **中文显示名**：用户可见输出优先使用中文显示名；首次出现英文协议标识时采用“中文显示名（英文标识）”，字段名、枚举值、路径、JSON/YAML key 等机器契约保持原值。

## 多 Agent 与降级

Task Driver 支持多 agent，但不依赖多 agent。

- 有 subagent/parallel agent 工具时，可以把 review、verification 或互不依赖的实现任务分派出去。
- 没有 subagent 能力时，自动使用 `single-agent`：同一个 agent 按 Brainstormer、Planner、Implementer、Reviewer、Verifier 顺序执行。
- 两种模式都必须使用同一套结构化交接 packet：`SpecPacket`、`PlanPacket`、`TaskResult`、`ReviewReport`、`VerificationReport`。
- 多 agent 输出只是证据，不是最终权威；controller 仍负责对照 spec/plan/ledger 做最终判断。

## 反例门禁

需要加入反例。反例能限制 agent 把“看起来像完成”的状态误判为完成。

典型违规：

- 没有 approved spec 就开始多文件实现。
- plan 写“适当处理异常、补充测试、完善逻辑”，但没有文件、命令和预期结果。
- plan 已确认后，每完成一个小步骤都问“是否继续”。
- 没有 fresh verification evidence 就说“已完成”。
- 没有 subagent 工具却声称“已派发 reviewer agent”。
- subagent 只返回散文总结，没有结构化 packet，却被当作通过。
- 同一 requirement 失败 2 轮后仍继续盲修。

## 当前状态

当前版本：v0.4.8

v0.4.8 将 Task Driver 从“插件 + 多 skill + standalone 兼容入口”的双模式收敛为单 skill 多阶段模式，便于 ccswitch/SkillHub 像安装 `flutter-forge` 一样安装完整目录。
