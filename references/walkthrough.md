# Walkthrough：端到端使用案例

本文用一个完整案例演示 Task Driver 从触发到交付的全流程。示例任务：**"给 CLI 工具添加 --verbose 标志来控制日志输出详细程度"**。

## 前置条件

- 项目是一个 Node.js CLI 工具，入口 `src/cli.ts`，日志通过 `src/logger.ts` 输出
- 当前只输出错误和警告，用户希望加 `--verbose` 输出调试信息

## 阶段 0：触发

用户输入：
```text
tdr- 给 CLI 工具加 --verbose flag，开启后输出调试级日志
```

## 阶段 1：Brainstorming（需求澄清）

### 事实收集

Agent 先读取相关文件，了解当前实现：

```text
[Agent 读取 src/cli.ts, src/logger.ts, package.json, tsconfig.json]
```

发现：
- `src/cli.ts` 使用 `commander` 解析参数
- `src/logger.ts` 是 `console.log` 的简单封装，无日志级别概念
- 没有现成的 `--verbose` flag

### 单问题澄清

已知事实足够，但日志级别设计有一个方案分叉需要确认：

```markdown
**已知事实**：当前 logger 无级别概念，只是 console.log 封装。CLI 使用 commander 解析参数。
**当前层级**：小项目/行为细节
**请确认**：--verbose 的行为范围是什么？

**选项**：
1. 仅控制台输出调试信息 -> 最简单，只改 logger 内部过滤
2. 同时写入调试日志文件 -> 需要引入文件写入，适用排障场景

**推荐**：选项 1，因为需求描述只提到"输出调试级日志"，未提及持久化。
**下一步**：确定范围后直接生成 spec。
```

用户选择选项 1。

### 产出 Spec

Agent 生成 `docs/task-driver/specs/2026-07-03--cli-verbose-flag.md`：

```markdown
# CLI --verbose Flag Spec

**Date:** 2026-07-03
**Quality level:** polished
**Status:** Approved

## Goal
CLI 工具支持 --verbose flag，开启后输出调试级日志到控制台。

## Target
- target_id: cli-verbose-flag
- target_statement: CLI 在用户启用 verbose 时输出调试信息，默认模式不输出调试信息。
- success_definition: AC-1 到 AC-5 均有 strong fresh evidence，且无未关闭 Critical/Important review finding。
- quality_level: polished
- stop_or_loop_conditions: AC 或验证策略错误回到 brainstorming；文件映射或任务顺序错误回到 planning；实现缺陷回到 executing。

## Scope
- 新增 --verbose / -v flag
- logger 支持 debug / info / warn / error 四个级别
- 默认级别为 info（--verbose 未开启时只输出 warn 及以上）
- --verbose 开启后输出所有级别

## Non-Goals
- 不写入日志文件
- 不改变现有命令的输出格式
- 不支持按模块过滤日志

## Proposed Design
CLI 解析 `--verbose` / `-v` 后设置 logger 全局级别；logger 负责按级别过滤输出，业务命令不透传 verbose 参数。

## Decision Trace
| 层级 | 决策点 | 选项摘要 | 用户/assumption 决策 | 对范围/验收/风险/验证的影响 |
|---|---|---|---|---|
| 整体目标 | verbose 要解决什么问题 | 控制台调试输出 / 日志文件 / 按模块过滤 | 控制台调试输出 | Scope 排除日志文件和模块过滤，AC 聚焦 CLI 输出 |
| 大类/规划轴 | 按哪条轴切第一版 | 最小用户路径 / 完整日志系统 / 配置化日志 | 最小用户路径 | 第一版只覆盖 flag、logger 级别、help 和错误输出回归 |
| 范围切片 | verbose 覆盖范围 | 仅控制台 / 同时写文件 | 仅控制台 | Non-Goals 明确不写日志文件 |
| 行为细节 | flag 行为 | `--verbose` only / `--verbose` + `-v` | `--verbose` + `-v` | AC-1 和 AC-3 分别验证长短参数 |
| 实现约束 | verbose 状态传递 | 全局 logger 状态 / 函数参数透传 / 环境变量 | 全局 logger 状态 | Constraints 禁止参数层层透传，测试 logger 状态 |

## Grilling Summary
- shared_understanding: true
- unresolved_branches: 无
- key_tradeoffs: 选择最小用户路径，优先验证 CLI 可见行为，不扩大到完整日志系统。
- rejected_paths: 写入调试日志文件、按模块过滤日志、函数参数层层透传。

## Design Tree Coverage
| 分支 ID | 分支 | 上游依赖 | 层级 | 状态 | 决策引用 | 阻塞项 |
|---|---|---|---|---|---|---|
| B1 | 控制台调试输出目标 | root | 整体目标 | decided | Decision Trace: 整体目标 | 无 |
| B2 | 最小用户路径规划轴 | B1 | 大类/规划轴 | decided | Decision Trace: 大类/规划轴 | 无 |
| B3 | 不写日志文件范围边界 | B2 | 范围切片 | out_of_scope | Non-Goals / rejected_paths | 无 |
| B4 | 长短 flag 行为 | B2 | 行为细节 | decided | AC-1 / AC-3 | 无 |
| B5 | 全局 logger 状态方案 | B4 | 实现约束 | decided | Constraints | 无 |
| B6 | CLI 命令验证策略 | B4 | 实现约束 | decided | AC-1..AC-5 | 无 |
| B7 | IO/权限风险 | B3 | 实现约束 | out_of_scope | rejected_paths | 无 |

## Alternatives Considered
- 写入调试日志文件：拒绝，因为用户目标只要求控制台调试输出，会扩大 IO、权限和清理风险。
- 按模块过滤日志：拒绝，因为第一版成功标准是 CLI verbose 行为，不需要模块级配置。

## Acceptance Criteria
| ID | 验收项 | 验证方式 |
|---|---|---|
| AC-1 | `cli --verbose` 输出包含调试信息 | `node dist/cli.js --verbose \| grep DEBUG` |
| AC-2 | `cli`（无 --verbose）不输出调试信息 | `node dist/cli.js \| grep -v DEBUG` |
| AC-3 | `cli -v` 与 `cli --verbose` 行为一致 | `node dist/cli.js -v \| grep DEBUG` |
| AC-4 | 现有命令的错误输出不受影响 | `node dist/cli.js --invalid 2>&1 \| grep Error` |
| AC-5 | 帮助信息中包含 --verbose 说明 | `node dist/cli.js --help \| grep verbose` |

## Constraints
- 使用 commander 的 `.option()` 方法
- 日志级别通过环境变量或全局状态传递，不通过函数参数层层透传

## Risks
- 低风险：改动局限在 cli.ts 和 logger.ts，不影响其他模块
```

## 阶段 2：Planning（制定计划）

### Spec 检查

Agent 自检 spec 无占位、无矛盾、Decision Trace 已闭合、Grilling Summary 显示 shared_understanding 为 true、AC 可验证 → 进入 planning。

### 产出 Plan 和 Ledger

Agent 生成 `docs/task-driver/plans/2026-07-03--cli-verbose-flag.md`：

```markdown
# CLI --verbose Flag Implementation Plan

## Goal
实现 --verbose flag，控制日志输出级别。

## Success Definition
- AC-1 到 AC-5 均有 fresh 命令证据覆盖，`--verbose` / `-v` 输出调试信息，默认模式不输出调试信息，现有错误输出和 help 行为保持正确。

## Verification Strategy
- 单元测试覆盖 logger 级别过滤和 CLI 参数解析，证据强度为 strong。
- 构建后 CLI 命令直接验证 `--verbose`、默认模式、`-v`、错误输出和 help 文案，覆盖 AC-1 到 AC-5。

## File Map
| File | Role | Change Type |
|------|------|-------------|
| src/logger.ts | 日志模块，新增级别过滤 | modify |
| src/cli.ts | CLI 入口，新增 --verbose flag | modify |
| src/logger.test.ts | logger 单元测试（新增） | create |

## Tasks

### T-001: logger 级别系统
- **文件**：src/logger.ts
- **步骤**：
  1. 定义 LogLevel 类型：`'debug' | 'info' | 'warn' | 'error'`
  2. 新增 `setLevel(level: LogLevel)` 和 `getLevel()` 函数
  3. 重构 log/debug/info/warn/error 函数，按级别过滤
- **验收**：`npm test -- --testPathPattern=logger` 通过
- **验证命令**：`npx ts-node -e "const l = require('./src/logger'); l.setLevel('debug'); l.debug('test')"` 应输出 "test"

### T-002: CLI --verbose flag
- **文件**：src/cli.ts
- **步骤**：
  1. 添加 `.option('-v, --verbose', '输出调试信息')`
  2. 解析后若 verbose 为 true，调用 `logger.setLevel('debug')`
  3. 否则调用 `logger.setLevel('info')`
- **验收**：`npm test -- --testPathPattern=cli` 通过
- **验证命令**：
  - `node dist/cli.js --verbose` 应输出调试信息
  - `node dist/cli.js` 不应输出调试信息
  - `node dist/cli.js -v` 与 `--verbose` 行为一致

### T-003: 帮助信息验证
- **文件**：src/cli.ts
- **步骤**：确认 commander 自动生成的 help 包含 --verbose 说明
- **验证命令**：`node dist/cli.js --help | grep verbose`

## Verification Plan
```bash
npm test                                    # 全量测试
node dist/cli.js --verbose | grep DEBUG     # AC-1
node dist/cli.js | grep -v DEBUG            # AC-2
node dist/cli.js -v | grep DEBUG            # AC-3
node dist/cli.js --invalid 2>&1 | grep Error # AC-4
node dist/cli.js --help | grep verbose      # AC-5
```

## Stop Conditions
- 任一测试失败且自动重试后仍失败
- 改动超出 src/logger.ts 和 src/cli.ts
```

Agent 同时创建 `docs/task-driver/ledgers/2026-07-03--cli-verbose-flag.md`。

## 阶段 3：Executing（执行）

### T-001 执行

Agent 按 TDD 先写测试，再实现，然后跑验证：

```text
[Agent] 写 src/logger.test.ts（失败测试）
[Agent] 实现 src/logger.ts 级别系统
[Agent] 运行 npm test -- --testPathPattern=logger → 通过
[Agent] 写入 TaskResult 和 ReviewReport 到 ledger
[Agent] 追加 Resume Checkpoint
```

### T-002 执行

```text
[Agent] 写 CLI 测试
[Agent] 实现 --verbose flag
[Agent] 运行验证命令 → 全部通过
[Agent] Scope Drift Detector：改动文件在 File Map 内，无漂移
[Agent] 写入 TaskResult 和 ReviewReport
```

### T-003 执行

```text
[Agent] 验证 help 输出包含 --verbose → 通过
[Agent] 写入 TaskResult 和 ReviewReport
```

## 阶段 4：Verification（验证）

### 全量验证

Agent 运行 plan 中的全部验证命令：

```text
$ npm test → 8 passed, 0 failed
$ node dist/cli.js --verbose | grep DEBUG → [DEBUG] ...
$ node dist/cli.js | grep -v DEBUG → (无 DEBUG 输出)
$ node dist/cli.js -v | grep DEBUG → [DEBUG] ...
$ node dist/cli.js --invalid 2>&1 | grep Error → Error: unknown option
$ node dist/cli.js --help | grep verbose → -v, --verbose  输出调试信息
```

### 完成审计

```markdown
| AC ID | Acceptance Criterion | Evidence | Strength | Status |
|-------|---------------------|----------|----------|--------|
| AC-1 | --verbose 输出调试信息 | `node dist/cli.js --verbose \| grep DEBUG` → [DEBUG] test message | strong | met[满足] |
| AC-2 | 无 --verbose 不输出调试信息 | `node dist/cli.js \| grep -v DEBUG` → (空) | strong | met[满足] |
| AC-3 | -v 与 --verbose 行为一致 | `node dist/cli.js -v \| grep DEBUG` → 同 AC-1 | strong | met[满足] |
| AC-4 | 错误输出不受影响 | `node dist/cli.js --invalid 2>&1 \| grep Error` → 正常 | strong | met[满足] |
| AC-5 | help 包含 --verbose | `node dist/cli.js --help \| grep verbose` → 包含说明 | strong | met[满足] |
```

### 质量评分

```yaml
quality_score:
  overall: 4.4
  dimensions:
    correctness: 5
    completeness: 4
    robustness: 4
    maintainability: 5
    usability: 4
  threshold: 4
  decision: pass
```

### User Acceptance Gate

Agent 先输出验收前自检表，确认 Plan tasks、Review reports、AC coverage、Verification strategy、Scope drift、Quality gate 和 Residual risk 无 fail，再输出最终报告并等待用户确认。用户回复确认后，状态更新为 `accepted_by_user`。

## 关键要点

1. **触发即进入流程**：`tdr-` 前缀触发 Task Driver，不会跳过阶段。
2. **澄清只问一个**：即使有多个不确定点，每轮只问最高影响的决策。
3. **先证据后声明**：verification 阶段必须运行命令、贴结果，不能说"看起来没问题"。
4. **中断可续传**：每个 TaskResult 后写 checkpoint，中断后可从断点继续。
5. **反例门禁全程生效**：每个阶段前读对应 counterexamples，避免常见错误。
