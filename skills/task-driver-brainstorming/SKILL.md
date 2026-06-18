---
name: task-driver-brainstorming
description: "需求澄清与 spec 阶段。用于 task-driver 开工前：事实收集、深度澄清、方案比较、明确范围/非目标/验收/质量层级，并产出 approved spec 与 SpecPacket。"
---

# 需求澄清与 Spec 阶段

把粗糙请求变成 approved spec。此阶段不得写实现代码，不得脚手架化方案，也不得直接输出最终实施计划。

## 必做清单

1. 读取当前事实：文件、文档、git 状态、日志、报错、已有 spec/plan、相关命令。
2. 判断任务是否过大；过大时拆成可独立交付的第一片。
3. 一次只问一个关键问题，直到决策树闭合。
4. 多方案时给出 2-3 个方案、取舍和推荐。
5. 展示 spec，并取得用户确认。
6. 保存 approved spec：`docs/task-driver/specs/YYYY-MM-DD--slug.md`。
7. 按 `skills/task-driver/SKILL.md` 的 packet contract 写 `SpecPacket` 到 ledger 或 plan 草稿。
8. 自检 spec：无占位、矛盾、模糊验收、范围漂移。

## 澄清标准

必须闭合：

- Why：用户真实场景和期望收益。
- What：核心交付物和 2-5 个关键行为。
- User：使用者和能力水平。
- Success：具体验收标准和证据来源。
- Quality：MVP / 精打磨 / 生产级。
- Scope：包含内容和明确非目标。
- Constraints：技术、时间、安全、合规、平台、风格、依赖限制。
- Trade-offs：可裁剪项和不可裁剪项。

只问会改变 spec 的问题。能给参考答案时，给 2-3 个选项帮助用户决策。

## Spec 模板

```markdown
# [任务名] Spec

**Date:** YYYY-MM-DD
**Quality level:** MVP | Polished | Production-grade
**Status:** Draft | Approved

## Goal
[一句话目标]

## User And Scenario
[谁在什么场景下为什么使用]

## Scope
- [包含行为]

## Non-Goals
- [明确排除行为]

## Proposed Design
[架构、流程、UI/API 行为、数据流或内容结构]

## Alternatives Considered
- [方案]: [取舍和接受/拒绝原因]

## Acceptance Criteria
- [可观察要求 + 验证方式]

## Constraints
- [精确约束]

## Risks
- [风险和缓解]
```

## 阶段输出

输出 `SpecPacket`。字段以 `skills/task-driver/SKILL.md` 的结构化交接 Packet 为准；本阶段至少填入 spec 路径、目标、用户场景、scope、non-goals、acceptance criteria、constraints、risks、quality level、是否获得用户确认。

## 自检门禁

确认 spec ready 前：

- 搜索 `TBD`、`TODO`、`later`、`maybe`、`适当处理`、模糊验收。
- 每条验收标准必须有证据来源。
- 非目标必须能阻止明显范围漂移。
- spec 必须小到能被一个 plan 执行；否则拆分。
