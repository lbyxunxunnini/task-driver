# Quick Start

30 秒判断是否启用 Task Driver：

```text
是否跨 2 个以上文件/模块？
  是 -> 用 Task Driver
  否 -> 下一问

目标、范围、验收、质量层级是否任一不清楚？
  是 -> 用 Task Driver
  否 -> 下一问

目标是否包含“全部 / 完整 / 100% / 迁移 / 覆盖”？
  是 -> 用 Task Driver，并先定义 scope_denominator
  否 -> 下一问

是否涉及数据、权限、安全、发布、迁移、外部服务或破坏性操作？
  是 -> 用 Task Driver
  否 -> 下一问

是否需要可恢复进度、跨阶段验证或用户最终验收？
  是 -> 用 Task Driver
  否 -> 普通执行即可
```

## Mode Picker

| 任务特征 | gate_mode | execution_mode |
|---|---|---|
| 单文件低风险、可一轮完成、有确定性验证 | `lite` | `single-agent` |
| 跨 2-5 文件、不涉及高风险领域 | `standard` | `single-agent` 或 `multi-agent-review` |
| 安全、权限、数据、发布、迁移、公共 API、生产级 | `strict` | 优先 `multi-agent-review` |
| 互不重叠的独立任务，且 plan 定义合并规则 | `standard` 或 `strict` | `multi-agent-parallel` |

## Stop Or Continue

继续执行：

- approved plan 中仍有 pending / in_progress 任务。
- 下一步已由 PlanPacket 明确写出。
- 只是完成了一个阶段、批次、小目标或单个任务。

停下问用户：

- 目标、范围、AC、质量层级或风险边界未闭合。
- scope_denominator、target_principles、拆解轴、目标覆盖矩阵或功能级验证口径未闭合。
- 继续会扩大 scope、删除/覆盖/发布/合并/丢弃工作。
- 计划假设错误，需要 plan-revision。
- 验证失败 2 轮后仍未闭合。

## Final Delivery Minimum

最终请求用户验收前必须有：

- SpecPacket：目标、scope_denominator、target_principles、AC、质量层级和 approved 状态。
- PlanPacket：gate_mode、execution_mode、target_coverage_matrix、decomposition_strategy、任务、文件、功能级验证和停机条件。
- TaskResult：每个任务的文件、命令、证据和 AC 覆盖。
- ReviewReport：每个任务的评审结果。
- VerificationReport：每条 AC 和目标单元的 fresh functional evidence、验收前自检、自检优化循环和 `delivery_acknowledged_by_user: pending`。

## Examples

- `references/walkthroughs/lite.md`：低风险单文件修改。
- `references/walkthroughs/standard.md`：跨文件 bugfix。
- `references/walkthroughs/strict.md`：高风险发布/权限/数据类任务。
