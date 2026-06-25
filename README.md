# Task Driver

Task Driver 是面向 agent 重任务的结构化工作流包。目标是把一个任务从“模糊请求”推进到“可验证交付”：事实收集、深度澄清、spec、plan、连续执行、TDD/评审、verification。

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

Task Driver 支持两种安装形态。二选一即可，推荐优先使用插件形态。

### 方式 A：作为 Codex 插件安装（推荐）

适合：Codex 支持插件、本项目需要暴露 5 个阶段 skill、希望后续继续扩展 hooks/MCP/marketplace。

插件入口：

```text
.codex-plugin/plugin.json
```

运行时 skill 来源：

```text
skills/
```

安装后暴露 5 个 skill：

- `task-driver`：总控入口。
- `task-driver-brainstorming`：事实收集、澄清、方案比较、spec。
- `task-driver-planning`：计划、文件映射、任务拆解、验证命令、ledger。
- `task-driver-executing`：连续执行、TDD、任务评审、ledger 更新。
- `task-driver-verification`：最终证据、验收审计、残余风险。

如果你用个人插件目录，常见放置方式是：

```text
~/plugins/task-driver/
  .codex-plugin/plugin.json
  skills/
```

然后通过 Codex 的插件安装/刷新流程加载该插件。插件形态下，根目录 `SKILL.md` 只是 standalone 兼容入口，不参与插件运行入口。

### 方式 B：作为单 skill 安装

适合：当前工具不支持插件，只支持传统 skill 目录。

单 skill 入口：

```text
SKILL.md
```

常见放置方式是把本项目目录作为一个 skill 放到 skill 搜索路径中，例如：

```text
~/.codex/skills/task-driver/
  SKILL.md
```

根目录入口名是 `task-driver-standalone`，用于避免递归扫描环境中和 `skills/task-driver/SKILL.md` 的 `task-driver` 重名。

如果运行环境不会扫描嵌套目录，根 `SKILL.md` 是最小入口；复杂任务中它会指向 `skills/task-driver/SKILL.md` 获取完整 packet、多 agent 和阶段交接规则。

如果运行环境会扫描嵌套目录，通常会看到：

- `task-driver-standalone`：根目录薄入口。
- `task-driver`：完整控制器。
- 4 个阶段 skill。

### 不要重复安装

根目录 `SKILL.md` 和 `skills/task-driver/SKILL.md` 服务于不同安装形态：

- 插件安装：`.codex-plugin/plugin.json` 指向 `./skills/`，使用 `skills/task-driver/SKILL.md`，根 `SKILL.md` 不参与插件入口。
- 单 skill 安装：使用根 `SKILL.md` 的 `task-driver-standalone`，适合不支持插件的环境。

不要同时安装“根目录单 skill”和“插件形态”，否则可能出现重复入口。

检查点：

- 如果 Codex 里出现一个 `task-driver` 和 4 个阶段 skill，说明你在用插件形态，正常。
- 如果只出现一个 `task-driver-standalone`，说明你在用根单 skill 形态，正常。
- 如果同时出现 `task-driver-standalone`、`task-driver` 和 4 个阶段 skill，说明运行时递归扫描了嵌套目录，入口不会同名冲突；复杂任务优先用 `task-driver`。
- 如果同时通过插件和单 skill 手动安装了同一份项目，保留一种安装方式即可。

## 工作流

1. **事实收集**：先查项目、文件、git、日志和已有文档。
2. **深度澄清**：先 Why，再 scope、success、quality、constraints。
3. **Spec**：保存到 `docs/task-driver/specs/YYYY-MM-DD--slug.md`。
4. **Plan**：保存到 `docs/task-driver/plans/YYYY-MM-DD--slug.md`。
5. **Ledger**：保存到 `docs/task-driver/ledgers/YYYY-MM-DD--slug.md`。
6. **执行**：确认后连续推进，行为变化优先 TDD。
7. **评审**：每个有意义任务检查 spec compliance 和质量问题。
8. **验证**：最终对照验收标准给出证据表。

## 治理门禁

- **重任务判定**：跨 2 个以上文件/模块，或目标、范围、验收、质量层级不清楚，或涉及数据、权限、安全、发布、迁移、外部服务、破坏性操作时，必须走 Task Driver。
- **明显方案分叉**：会改变 API、数据模型、用户流程、依赖、验证方式、风险边界、交付范围或回滚方式的选择，必须在 spec/plan 阶段确认。
- **澄清分层**：Goal、Scope、Non-goals、Acceptance Criteria、Constraints、Quality Level 是必填门禁；User scenario、Risks、Trade-offs、Alternatives 按需补充。
- **品质层级**：MVP 覆盖核心路径；精打磨覆盖主要边界和错误状态；生产级覆盖安全、权限、性能、兼容、观测、回滚/迁移和完整回归。
- **执行-验证循环**：同一 requirement 最多 2 轮；仍失败则进入 `blocked`、`partial` 或 `plan-revision`。
- **证据强度**：`strong` 才能标 `Met`；`medium` 最多 `Partial`；`weak` / `stale` 必须 `Not met` 或 `Blocked`。

## 多 Agent 与降级

Task Driver 支持多 agent，但不依赖多 agent。

- 有 subagent/parallel agent 工具时，可以把 review、verification 或互不依赖的实现任务分派出去。
- 没有 subagent 能力时，自动降级为 single-agent：同一个 agent 按 Brainstormer、Planner、Implementer、Reviewer、Verifier 顺序执行。
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

## 70 分标准

当前版本补齐了关键工作流能力：

- 持久化 spec/plan/ledger。
- 多阶段 skill 拆分。
- TDD 优先规则。
- 任务级 review gate。
- 分支/工作区安全前置检查。
- 上下文恢复规则。
- 完成前 verification gate。
- 可选多 agent 执行与 single-agent 降级协议。
- 运行时 skill 使用中文书写，方便调试，但不限定中文语境。
- Codex 插件 manifest。
- APM issue 修复：循环退出、澄清分层、操作化判定、证据强度、品质层级、Red Flags。

暂未包含：

- 没有完整 hooks/bootstrap 体系。
- 没有内置脚本生成 review package 或 task brief。
- 没有专门的 subagent prompt 模板。
- 没有行为 eval harness。
- 没有 marketplace 发布配置。

## 文件结构

```text
task-driver/
  .codex-plugin/plugin.json
  SKILL.md      # task-driver-standalone 薄入口
  skills/
    task-driver/
    task-driver-brainstorming/
    task-driver-planning/
    task-driver-executing/
    task-driver-verification/
  README.md
  CHANGELOG.md
```

## 版本

当前版本：v0.4.4
