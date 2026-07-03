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
**只需要你拍板 1 个问题**：--verbose 的行为范围是什么？

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
**Quality level:** 精打磨
**Status:** Approved

## Goal
CLI 工具支持 --verbose flag，开启后输出调试级日志到控制台。

## Scope
- 新增 --verbose / -v flag
- logger 支持 debug / info / warn / error 四个级别
- 默认级别为 info（--verbose 未开启时只输出 warn 及以上）
- --verbose 开启后输出所有级别

## Non-Goals
- 不写入日志文件
- 不改变现有命令的输出格式
- 不支持按模块过滤日志

## Acceptance Criteria
| ID | Criterion |
|----|-----------|
| AC-1 | `cli --verbose` 输出包含调试信息 |
| AC-2 | `cli`（无 --verbose）不输出调试信息 |
| AC-3 | `cli -v` 与 `cli --verbose` 行为一致 |
| AC-4 | 现有命令的错误输出不受影响 |
| AC-5 | 帮助信息中包含 --verbose 说明 |

## Constraints
- 使用 commander 的 `.option()` 方法
- 日志级别通过环境变量或全局状态传递，不通过函数参数层层透传

## Risks
- 低风险：改动局限在 cli.ts 和 logger.ts，不影响其他模块
```

## 阶段 2：Planning（制定计划）

### Spec 检查

Agent 自检 spec 无占位、无矛盾、AC 可验证 → 进入 planning。

### 产出 Plan 和 Ledger

Agent 生成 `docs/task-driver/plans/2026-07-03--cli-verbose-flag.md`：

```markdown
# CLI --verbose Flag Implementation Plan

## Goal
实现 --verbose flag，控制日志输出级别。

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

Agent 输出最终报告，等待用户确认。用户回复确认后，状态更新为 `accepted_by_user`。

## 关键要点

1. **触发即进入流程**：`tdr-` 前缀触发 Task Driver，不会跳过阶段。
2. **澄清只问一个**：即使有多个不确定点，每轮只问最高影响的决策。
3. **先证据后声明**：verification 阶段必须运行命令、贴结果，不能说"看起来没问题"。
4. **中断可续传**：每个 TaskResult 后写 checkpoint，中断后可从断点继续。
5. **反例门禁全程生效**：每个阶段前读对应 counterexamples，避免常见错误。
