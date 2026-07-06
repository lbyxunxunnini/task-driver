# Glossary

面向用户输出时，优先使用中文显示名。首次出现英文协议标识、状态值、字段名、模式名或阶段名时，使用”中文显示名[英文标识]”格式；后续同一回复内可只用中文显示名。代码块、字段表、路径、JSON/YAML key、枚举值本身保持英文原值。

不得为了中文化修改机器契约本身：skill 名、文件路径、frontmatter key、JSON key、YAML key、字段名、枚举值、命令、代码块内容必须保持原值；只改变面向用户的显示方式。

示例：

- 需求规格交接包[SpecPacket]
- 计划交接包[PlanPacket]
- 任务结果[TaskResult]
- 用户验收门禁[User Acceptance Gate]
- 等待用户验收[`awaiting_user_acceptance`]

| 英文标识 | 中文显示名 |
|---|---|
| Task Driver | 任务驱动框架 |
| task-driver | 任务驱动标识 |
| skill | 技能 |
| agent | 智能体 |
| workflow | 工作流 |
| task-management | 任务管理 |
| spec | 需求规格 |
| plan | 计划 |
| ledger | 执行台账 |
| packet | 交接包 |
| schema | 结构定义 |
| brainstorming | 需求澄清阶段 |
| planning | 计划阶段 |
| executing | 执行阶段 |
| verification | 验证阶段 |
| Brainstormer | 需求澄清者 |
| Planner | 计划制定者 |
| Implementer | 实现者 |
| Reviewer | 评审者 |
| Verifier | 验证者 |
| SpecPacket | 需求规格交接包 |
| PlanPacket | 计划交接包 |
| TaskResult | 任务结果 |
| ReviewReport | 评审报告 |
| VerificationReport | 验证报告 |
| approved | 已确认 |
| draft | 草稿 |
| superseded | 已被替代 |
| degraded-single-skill | 降级单技能模式 |
| mode | 执行模式 |
| strict | 严格模式 |
| standard | 标准模式 |
| lite | 轻量模式 |
| single-agent | 单智能体模式 |
| multi-agent-review | 多智能体评审模式 |
| multi-agent-parallel | 多智能体并行模式 |
| subagent | 子智能体 |
| parallel agent | 并行智能体 |
| review gate | 评审门禁 |
| verification gate | 验证门禁 |
| User Acceptance Gate | 用户验收门禁 |
| Scope Drift Detector | 范围漂移检测器 |
| File Map | 文件映射 |
| Iteration Log | 迭代记录 |
| Plan Revision Protocol | 计划修订协议 |
| Diff From | 相比上一版差异 |
| Single Source of Truth | 单一事实源 |
| Cross-Packet References | 交接包跨引用 |
| quality level | 质量层级 |
| MVP | 最小可用版 |
| Polished | 精打磨 |
| Production-grade | 生产级 |
| Why | 目的 |
| What | 交付内容 |
| Success | 成功标准 |
| Quality | 质量要求 |
| Scope | 范围 |
| Constraints | 约束 |
| User scenario | 用户场景 |
| Trade-offs | 取舍 |
| Risks | 风险 |
| Alternatives | 备选方案 |
| Goal | 目标 |
| Non-Goals | 非目标 |
| Proposed Design | 建议方案 |
| Alternatives Considered | 已考虑的备选方案 |
| Acceptance Criteria | 验收标准 |
| Implementation Plan | 实施计划 |
| Global Constraints | 全局约束 |
| Interfaces | 接口 |
| Tasks | 任务 |
| Task | 任务 |
| Owner role | 负责人角色 |
| Files | 文件 |
| Acceptance | 验收项 |
| Status | 状态 |
| Predecessor | 前序版本 |
| Run | 运行命令 |
| Expected | 预期结果 |
| Actual | 实际结果 |
| Evidence | 证据 |
| evidence_strength | 证据强度 |
| strong | 强证据 |
| medium | 中等证据 |
| weak | 弱证据 |
| stale | 过期证据 |
| blocked | 受阻 |
| partial | 部分完成 |
| not_met | 未满足 |
| met | 已满足 |
| awaiting_user_acceptance | 等待用户验收 |
| accepted_by_user | 用户已接受 |
| rejected_by_user | 用户已拒绝 |
| pending | 待处理 |
| in_progress | 进行中 |
| done | 已完成 |
| pass | 通过 |
| fail | 失败 |
| needs_fix | 需要修复 |
| Critical | 严重 |
| Important | 重要 |
| Minor | 次要 |
| backlog | 待办积压 |
| correctness | 正确性 |
| completeness | 完整性 |
| robustness | 鲁棒性 |
| maintainability | 可维护性 |
| usability | 可用性 |
| overall | 综合评分 |
