# Task Driver Loop & Handoff Upgrade Spec

**Date:** 2026-06-23
**Quality level:** Polished
**Status:** Approved

## Goal

为 Task Driver 协议补齐三类机制：循环驱动器、目标增量检测、交接契约化，使现有“边界式”协议升级为“运转式”协议。

## User And Scenario

使用者：Task Driver 自身的 controller 与各阶段 skill。
场景：执行重任务时，从 spec → plan → execute → review → verify 的 packet 交接需要可追溯、可校验、可恢复；同一 requirement 多轮循环时需状态可继承；用户对最终交付物需要显式验收点。

## Scope

合并以下 11 条补丁到现有 5 个 SKILL.md 与 1 个根目录 SKILL.md。

**A. 循环与反馈（5 条）**

- A1 Iteration Packet：Ledger 增加 `iteration_log[]`。
- A2 User Acceptance Gate：VerificationReport 后增加 `delivery_acknowledged_by_user` 显式确认点。
- A3 AC 增量打点：TaskResult packet 增加 `ac_coverage[]`。
- A4 Scope Drift Detector：Executing 阶段每个任务结束时强制比对 `files_changed` 与 plan File Map。
- A5 Plan-revision 协议：明确 plan-revision 的回流去向与版本字段。

**B. 交接结构化（6 条）**

- B1 Packet 字段表正式化：主控 SKILL.md YAML 升级为字段表。
- B2 Task ID 唯一锁定：plan / packet / ledger 全部用 `T-NNN` ID 引用。
- B3 Packet 状态机：五种 packet 显式 status 枚举与迁移合法性。
- B4 跨 packet 引用规则：TaskResult ↔ PlanPacket、ReviewReport ↔ TaskResult、VerificationReport ↔ Spec.AC 必须 ID 引用。
- B5 Evidence 子结构化：Ledger Evidence 升级为多字段对象。
- B6 Plan 任务清单与 PlanPacket 单源化：**PlanPacket 为权威**，plan markdown 任务清单为渲染产物。

## Non-Goals

- 不引入运行时校验脚本，仅在文档层定义契约。
- 不改变 5 阶段流程顺序、不改变 2 轮循环上限、不改变品质三档。
- 不引入新 packet 种类，仅扩展已有五种。
- 不写自动化工具（CLI/校验器/渲染器），保持 markdown-only。

## Proposed Design

文件级影响：

| 文件 | 改动 | 主要变化 |
|---|---|---|
| `skills/task-driver/SKILL.md` | 修改 | 字段表 + 状态机 + 引用规则 + 单源条款 + 用户验收门 |
| `skills/task-driver-brainstorming/SKILL.md` | 修改 | AC 增加 `id` 字段要求 |
| `skills/task-driver-planning/SKILL.md` | 修改 | Plan 模板加 Task ID；Ledger 模板加 iteration_log + 结构化 Evidence；plan-revision 字段 |
| `skills/task-driver-executing/SKILL.md` | 修改 | Scope Drift 强制检查 + TaskResult.ac_coverage |
| `skills/task-driver-verification/SKILL.md` | 修改 | User Acceptance Gate + 引用 Spec AC ID |
| `SKILL.md`（根目录） | 修改 | 同步契约要点到单 skill 入口 |
| `CHANGELOG.md` | 修改 | v0.4.3 升级条目 |

执行顺序：B1 → B2 → B3 → B4 → B5 → B6 → A3 → A4 → A1 → A5 → A2。

## Alternatives Considered

- 引入 JSON Schema 文件并写校验器：拒绝，需运行时支持，违反 Non-Goals。
- 仅做 A 类不做 B 类：拒绝，A3/A4 依赖 B2/B4 的 ID 体系。
- 全部塞进主控 SKILL.md：拒绝，违反主控/子阶段职责分层。
- B6 选 plan markdown 为权威：拒绝，与 A3/A4/B4 的 ID 稳定性需求冲突。

## Acceptance Criteria

| ID | 验收项 | 验证方式 |
|---|---|---|
| AC-1 | 五种 packet 在主控 SKILL.md 以字段表形式出现，含 name/type/required/enum/description | 主控含字段表头与 ≥3 字段抽查 |
| AC-2 | Plan 模板任务条目含 `T-NNN` 格式 ID；TaskResult / ReviewReport packet 字段含对应引用字段 | grep `T-0` 模式；字段表含引用字段 |
| AC-3 | 每种 packet 定义 status 枚举与迁移规则文字描述 | 主控含 "Status enum" 与 "Transition" 段落 |
| AC-4 | Spec 模板的 AC 段落要求 `AC-N` 形式 ID | brainstorming 模板含示例 |
| AC-5 | TaskResult packet 含 `ac_coverage[]` 字段，executing SKILL.md 描述如何填写 | 字段表抽查；executing 含 ac_coverage 说明 |
| AC-6 | Executing SKILL.md 含 Scope Drift Detector 段落，定义比对规则与触发停机条件 | grep "Scope Drift" 段；含 files_changed vs File Map |
| AC-7 | Ledger 模板含 `iteration_log[]` 段，字段含 attempt/hypothesis/command/result/next_assumption | planning ledger 模板对应段 |
| AC-8 | Plan 模板含 plan-revision 字段（version、predecessor、diff_summary） | planning 含对应段 |
| AC-9 | Verification SKILL.md 含 User Acceptance Gate 段落与 `delivery_acknowledged_by_user` 字段 | grep "User Acceptance Gate" |
| AC-10 | Ledger Evidence 段升级为结构化字段（timestamp/command/exit_code/output_excerpt/covers_requirement_ids/strength） | planning ledger 模板对应段 |
| AC-11 | 主控 SKILL.md 明示 PlanPacket 为任务清单单源、plan markdown 与 packet 同步规则 | grep "Single Source" 或同义条款 |
| AC-12 | CHANGELOG.md 含本次升级条目，列出 11 条补丁清单 | 读 CHANGELOG |
| AC-13 | 现有约束未被破坏：5 阶段、2 轮循环、品质三档、反例门禁清单仍存在且语义一致 | 读 SKILL.md 比对 |
| AC-14 | spec / plan / ledger 三份文档按命名规范创建 | 路径检查 |

## Constraints

- 仅修改 markdown，不引入代码。
- 不破坏现有 packet 字段命名（向后兼容：旧字段保留，新字段增量）。
- 任意单份 SKILL.md 单独阅读仍可运转。
- 中文为主，与现有文档语种一致。
- 根目录 `SKILL.md` 保留单 skill 兼容性。

## Risks

- R1 主控 SKILL.md 体积膨胀。缓解：紧凑表格；详细枚举值放子阶段。
- R2 旧 plan 文档不兼容新 ID 体系。缓解：CHANGELOG 注明从本次起新 plan 适用，旧 plan 不强制回填。
- R3 用户验收门与“已确认 plan 后不得每步问继续”张力。缓解：限定验收门只在 verification 之后触发一次。
- R4 Scope Drift Detector markdown 协议无法机器执行。缓解：写成强制 checklist + 反例样例。
- R5 B6 单源选择漂移。已定：PlanPacket 为权威，plan markdown 清单为渲染产物，漂移以 packet 为准。
