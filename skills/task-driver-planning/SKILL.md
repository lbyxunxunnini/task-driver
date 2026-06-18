---
name: task-driver-planning
description: "计划阶段。用于 approved spec 之后、执行之前：创建实施 plan、文件映射、接口、任务拆解、TDD/验证命令、review gate、ledger 和 PlanPacket。"
---

# 计划阶段

写出一个新 agent 也能执行的计划。Plan 是执行契约；确认后不应再靠连续追问推进。

## 必要输入

- Approved spec，内联或位于 `docs/task-driver/specs/`。
- 当前项目事实：文件结构、实现模式、测试命令、依赖管理、git 状态。
- 用户约束和质量层级。

缺少且本地无法查到的信息，必须先问。

## Plan 要求

保存到 `docs/task-driver/plans/YYYY-MM-DD--slug.md`。

必须包含：

- 目标和 spec 路径。
- 从 spec 复制的全局约束。
- 执行模式：`single-agent`、`multi-agent-review` 或 `multi-agent-parallel`。
- 文件映射：创建/修改/测试/文档路径及职责。
- 接口：函数、命令、配置键、schema 或公开行为。
- 任务拆分：每个任务能独立验证和评审。
- 行为变化：TDD 步骤、预期失败、最小实现、通过命令、重构边界。
- 非代码变化：确定性的验证步骤。
- 每个任务的 review gate。
- ledger 路径：`docs/task-driver/ledgers/`。
- 每个任务需要消费和产出的 packet；字段以 `skills/task-driver/SKILL.md` 的 packet contract 为准。
- 停机条件和回滚说明。

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
**Mode:** single-agent | multi-agent-review | multi-agent-parallel
**Quality level:** MVP | Polished | Production-grade
**Status:** Draft | Approved

## Goal
[一句话目标]

## Global Constraints
- [精确约束]

## File Map
- Create: `path` - [职责]
- Modify: `path` - [职责]
- Test: `path` - [职责]

## Interfaces
- [名称/签名/命令/schema 和消费者]

## Tasks

### Task 1: [名称]
**Owner role:** Implementer
**Files:** [精确路径]
**Acceptance:** [来自 spec 的验收]
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
- [最终命令和预期结果]

## Stop Conditions
- [必须暂停回问的情况]
```

## Ledger 模板

执行前创建：

```markdown
# [任务名] Progress Ledger

**Spec:** docs/task-driver/specs/YYYY-MM-DD--slug.md
**Plan:** docs/task-driver/plans/YYYY-MM-DD--slug.md
**Mode:** single-agent | multi-agent-review | multi-agent-parallel
**Started:** YYYY-MM-DD

## Status
- Task 1: pending

## Packets
- SpecPacket: [path or inline summary]
- PlanPacket: [tasks and verification]
- TaskResult: pending
- ReviewReport: pending
- VerificationReport: pending

## Evidence
- [timestamp] [command] -> [result]

## Review Findings
- [finding/status]

## Decisions
- [decision/source]
```

## 阶段输出

输出 `PlanPacket` 并创建 ledger。字段以 `skills/task-driver/SKILL.md` 的结构化交接 Packet 为准；本阶段至少填入 plan 路径、ledger 路径、执行模式、任务 id、owner role、objective、files、steps、verification、stop conditions。

## 自检门禁

交给用户确认前：

- 每条 spec 验收必须映射到任务或验证命令。
- 搜索占位词。
- 检查任务顺序、接口名称、路径一致。
- 检查 ledger 路径存在于 plan。
- 一次性请求完整 plan 确认；确认后执行阶段不逐步讨确认。
