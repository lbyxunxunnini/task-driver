# Quality Rubric

Quality Rubric 用于 verification 阶段回答“做得有多好”，不替代 Acceptance Criteria 和 Evidence Strength。

品质层级的机器枚举统一为 `mvp` / `polished` / `production`；用户可见文本可显示为 MVP / 精打磨 / 生产级。`quality_score.threshold` 必须按机器枚举映射。

## When to Score

VerificationReport 写入前，若任务满足任一条件，必须给出质量评分：

- 用户要求“精打磨”或“生产级”。
- 任务修改用户可见行为、公共 API、权限、安全、数据、发布、迁移、依赖或构建配置。
- 任务跨 2 个以上文件或 2 个以上模块。
- ReviewReport 存在 Minor backlog 或 deferred item。
- VerificationReport 中任一 AC 为 `partial`。

MVP 且低风险的一次性任务可以不评分，但必须在 VerificationReport 记录 `quality_score: N/A` 和理由。

## Score Fields

质量评分写入 VerificationReport 或 ledger Evidence 段：

```yaml
quality_score:
  overall: 1.0-5.0 | N/A
  dimensions:
    correctness: 1-5
    completeness: 1-5
    robustness: 1-5
    maintainability: 1-5
    usability: 1-5 | N/A
  threshold: 3 | 4 | 4.5
  decision: pass | improve | blocked | N/A
  evidence_refs: [EV-N]
  rationale: string
```

## Dimension Rubric

| Dimension | 1 | 3 | 5 |
|---|---|---|---|
| correctness | 核心行为错误或未验证 | 核心行为正确，有直接证据 | 核心和关键边界都有 fresh evidence |
| completeness | 明显遗漏 AC 或 plan 项 | 主要 AC 覆盖，存在非关键缺口 | AC、非目标、边界和回归面都闭合 |
| robustness | 异常路径未考虑 | 主要错误状态有处理 | 失败、重试、回滚、权限/数据风险都有处理 |
| maintainability | 改动难读、偏离本地模式 | 基本符合本地模式 | 小范围、命名清楚、无无关重构、易回滚 |
| usability | 用户路径或文案粗糙 | 核心体验可用 | 空/错/加载/边界状态和文案都清楚 |

没有用户可见体验时，`usability` 可为 `N/A`，overall 按其余维度平均。

## Thresholds

- `mvp`（MVP）：threshold = 3。低于 3 必须回到 executing 或 blocked。
- `polished`（精打磨）：threshold = 4。低于 4 必须回到 executing、plan-revision 或 blocked。
- `production`（生产级）：threshold = 4.5。低于 4.5 必须回到 executing、plan-revision 或 blocked。

`overall` 不得高于 evidence 支持的 AC 状态：

- 任一关键 AC 为 `not_met` 或 `blocked`：decision 必须是 `blocked`。
- 任一关键 AC 为 `partial`：overall 最高 3.5，decision 最高 `improve`，除非用户 partial-accept。
- 存在 Critical / Important 未关闭 finding：decision 必须是 `blocked`。

## Improve Loop

评分低于 threshold 时：

1. 选出最低的 1-2 个维度。
2. 写明对应 AC、证据和缺口。
3. 若缺口仍在 approved scope 和 2 轮执行-验证上限内，回到 executing。
4. 若缺口暴露 plan/spec 错误，进入 plan-revision 或 brainstorming。
5. 若缺口依赖用户决策、权限、环境或外部服务，进入 blocked。

不得为了提高评分扩大 scope；需要扩大 scope 时必须触发 Plan Revision Protocol。
