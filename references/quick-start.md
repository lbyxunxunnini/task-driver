# Quick Start

## 30 秒判断

**你需要 Task Driver 吗？** 回答 3 个问题：

1. **是否跨 2+ 文件/模块？**
   - 是 → 用 Task Driver
   - 否 → 下一问

2. **目标、范围、验收、质量层级是否任一不清楚？**
   - 是 → 用 Task Driver
   - 否 → 下一问

3. **是否涉及数据、权限、安全、发布、迁移、外部服务或破坏性操作？**
   - 是 → 用 Task Driver
   - 否 → 普通执行即可

**选什么模式？**

| 任务特征 | 门禁模式[gate_mode] | 执行模式[execution_mode] |
|---|---|---|
| 单文件低风险、可一轮完成 | 轻量模式[lite] | 单智能体模式[single-agent] |
| 跨 2-5 文件、默认风险 | 标准模式[standard] | 单智能体模式[single-agent] 或 多智能体评审模式[multi-agent-review] |
| 安全、权限、数据、发布、迁移、生产级 | 严格模式[strict] | 优先 多智能体评审模式[multi-agent-review] |
| 互不重叠的独立任务 | 标准模式[standard] 或 严格模式[strict] | 多智能体并行模式[multi-agent-parallel] |

## 极简示例

**场景：** 用户要求修复一个跨 2 个文件的 bug

**第 1 轮：触发 Task Driver**
```
用户: tdr- 修复登录页面的样式 bug
```

**第 2 轮：需求澄清**
```
agent: 我需要确认几个问题...
用户: 目标是修复登录按钮的样式，范围是 login.css 和 button.css
```

**第 3 轮：计划确认**
```
agent: 我已制定计划，包含 2 个任务...
用户: 确认，开始执行
```

**第 4 轮：执行**
```
agent: 正在执行 T-001: 修改 login.css...
用户: 继续
```

**第 5 轮：验证**
```
agent: 验证完成，样式已修复，请确认
用户: 确认，任务完成
```

## 写入前预检（显式触发时必做）

用户显式触发 Task Driver（`tdr-` / `task-driver` / `/task-driver`）后，首次写入动作前必须完成：

1. 输出启动预检门声明（当前阶段、目标草案、是否有 approved spec、是否有 approved plan、本次动作类型）。
2. 确认写入屏障状态：
   - 无 approved spec 且无 approved plan → 屏障生效，只允许读取和澄清。
   - 有 approved spec 或 approved plan → 屏障解除，可执行写入。
3. 如果是小任务走内联路径，仍必须先产出内联 spec/plan 并让用户确认，不得以"任务小"跳过。

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
