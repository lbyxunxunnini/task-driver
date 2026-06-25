# Changelog

## v0.4.5 (2026-06-24)

### 改进

- **错误提示模板同步到子 skill**：将错误提示模板从主控 SKILL.md 同步到 `skills/task-driver/SKILL.md`，确保子 skill 执行时也能使用标准化提示格式。

## v0.4.4 (2026-06-23)

### 改进

- **错误提示模板标准化**：主控 SKILL.md 新增"错误提示模板"段，定义 5 种结构化模板：
  - 停机回问模板（问题类型、上下文、决策选项）
  - 验证失败模板（失败项、命令、结果、证据强度、下一步）
  - 循环退出模板（Iteration Log 表格、根因分析、状态建议）
  - 范围漂移模板（允许集 vs 实际改动、超出原因）
  - 阻塞状态模板（阻塞原因、解除条件、当前产出）
- 解决评分反馈：异常处理提示不够清晰易懂（原 4.0 分）

## v0.4.3 (2026-06-23) — SkillHub 首次发布

- SkillHub 发布成功：`task-driver-user-88546431@0.4.3`，skillId=`91498`
- SKILL.md 补齐 SkillHub frontmatter（slug、displayName、version、summary、tags、license）

## v0.4.3 (2026-06-23)

### 新增

- `B1 Packet 字段表正式化`：主控 SKILL.md 五种 packet YAML 示例升级为字段表（Field / Type / Required / Enum / Description），保留 YAML 简表作示例。
- `B2 Task ID 唯一锁定`：PlanPacket.tasks[].id 、 TaskResult.task_id 、 ReviewReport.task_id 统一使用 `T-NNN` 格式；planning Plan 模板任务标题改为 `### Task T-001`。
- `B3 Packet 状态机`：主控 SKILL.md 新增 “Packet Status & Transitions” 段，为 5 种 packet 定义 status 枚举与合法迁移；VerificationReport 新增 `awaiting_user_acceptance` 与 `accepted_by_user` 状态。
- `B4 跨 packet 引用规则`：主控 SKILL.md 新增 “Cross-Packet References” 段，明确 TaskResult ↔ PlanPacket / ReviewReport ↔ TaskResult / VerificationReport ↔ Spec.AC 以 ID 引用。
- `B5 Evidence 子结构化`：planning Ledger 模板 Evidence 段升级为 `timestamp / command / exit_code / output_excerpt / covers_requirement_ids / strength` 多字段列表项。
- `B6 PlanPacket 单源化`：主控 SKILL.md 新增 “Single Source of Truth: PlanPacket” 段；PlanPacket.tasks[] 为权威，plan markdown 任务清单为渲染产物，漂移以 packet 为准；planning 自检门禁增一一对应校验。
- `A1 Iteration Packet`：Ledger 模板新增 `## Iteration Log` 段，字段 `attempt / requirement_id / hypothesis / command / result / next_assumption / outcome`；主控、executing、verification 三处循环退出表述统一引用。
- `A2 User Acceptance Gate`：verification SKILL.md 新增 “User Acceptance Gate” 段；VerificationReport 增 `delivery_acknowledged_by_user` 字段，accept / reject / partial-accept 三选一，仅在验证后触发一次，不与“已确认 plan 后不得每步讨确认”冲突。
- `A3 AC 增量打点`：brainstorming Spec 模板 Acceptance Criteria 改为带 `AC-N` ID 的表格，自检门禁增 ID 化要求；TaskResult 增 `ac_coverage[]` 字段（元素 `{ac_id, covered: full/partial/none, evidence}`）；executing 执行循环增一步填写。
- `A4 Scope Drift Detector`：executing SKILL.md 新增 “Scope Drift Detector” 段；每个任务 TaskResult 写入前必须比对 `files_changed` 与 PlanPacket File Map，不一致停机回问；反例门禁追加相关违规项。
- `A5 Plan Revision Protocol`：planning 与主控 SKILL.md 新增 “Plan Revision Protocol” 段；Plan 模板顶部增 `Plan version` 与 `Predecessor`；v2+ 必填 `## Diff From v[N-1]`；前版状态置 `superseded`；spec 也错误时需回到 brainstorming 重写。

### 改进

- 根 `SKILL.md` 核心契约从 7 条扩展为 11 条，涵盖 ID 化、增量覆盖、范围锁定、计划修订、交付验收；反例门禁同步追加 5 项。
- verification 完成审计表增 `AC ID` 与 `Strength` 列，与证据强度合并表达。
- planning ledger 模板 Status / Decisions / Review Findings 段采用 `T-NNN` 与 timestamp 结构化记录。

### 兼容性

- 旧 packet 字段名称未修改，新字段均为增量；旧 plan / spec 不强制回填 ID 与 Plan version，仅从本版本起的新产物适用。
- 5 阶段、 2 轮循环上限、品质三档、反例门禁主体语义未变。

## v0.4.2 (2026-06-18)

### 修复

- `APM-WORKFLOW-001`：增加执行-验证循环退出条件；同一 requirement 最多 2 轮，仍失败进入 `blocked`、`partial` 或 `plan-revision`
- `APM-INSTRUCTION-001`：澄清标准分为必填门禁和按需补充，避免 8 项全阻塞
- `APM-INSTRUCTION-002`：操作化“重任务”和“明显方案分叉”的判定条件
- `APM-GOV-001`：验证报告增加证据强度和覆盖范围，避免二元 pass/fail
- `APM-GOV-002`：补充 MVP、精打磨、生产级的验收差异
- `APM-DESIGN-001`：说明 packet schema 单点定义是刻意取舍，避免 schema drift
- `APM-BP-001`：增加 Red Flags，预判“应该好了”“窄验证宣称全完成”等 agent 自欺信号

## v0.4.1 (2026-06-18)

### 改进

- 根入口更名为 `task-driver-standalone`，避免递归扫描时与 `skills/task-driver/SKILL.md` 同名冲突
- 根 `SKILL.md` 收敛为薄 bootstrap 入口；完整 packet、多 agent 和阶段交接规则集中到 `skills/task-driver/SKILL.md`
- 子阶段 skill 去除重复 YAML schema，只声明本阶段产出的 packet 和必填信息

## v0.4.0 (2026-06-18)

### 新增

- Codex 插件入口：`.codex-plugin/plugin.json`
- `skills/` 多 skill 结构：
  - `task-driver` 总控
  - `task-driver-brainstorming`
  - `task-driver-planning`
  - `task-driver-executing`
  - `task-driver-verification`
- 持久化工件规范：
  - `docs/task-driver/specs/YYYY-MM-DD--slug.md`
  - `docs/task-driver/plans/YYYY-MM-DD--slug.md`
  - `docs/task-driver/ledgers/YYYY-MM-DD--slug.md`
- Spec 模板、Plan 模板、Ledger 模板
- TDD 优先规则：行为变化必须先写失败测试，除非明确豁免或不可测试
- 任务级 review gate：spec compliance + code/content quality
- 分支/工作区 preflight：非小型修改不得默认在 `main`/`master` 上推进
- 上下文恢复规则：恢复时优先读取 ledger 和 git history
- 完成审计表格：逐条验收标准对照证据
- 可选多 agent 执行模式：`single-agent`、`multi-agent-review`、`multi-agent-parallel`
- single-agent 降级规则：不支持 subagent 时不得阻塞，必须由当前 agent 顺序扮演各角色
- 结构化交接 packet：`SpecPacket`、`PlanPacket`、`TaskResult`、`ReviewReport`、`VerificationReport`
- 根 `SKILL.md` 明确为单 skill 兼容入口，避免和插件子 skill 混淆
- 反例门禁：覆盖无 spec 开工、占位 plan、逐步讨确认、无验证声明完成、伪多 agent、非结构化 subagent 输出

### 改进

- 根 `SKILL.md` 从单一澄清流程升级为 Task Driver 运行契约
- 运行时 skill 使用中文书写，方便调试，但不把 skill 定位限定为中文语境
- 明确“小任务可简化”的条件，避免所有任务都被重流程拖慢
- 把“禁止假完成”升级为 fresh verification evidence gate
- 明确多 agent 输出只是证据，最终判断仍由 controller 对照 spec/plan/ledger 完成
- README 更新为插件/单 skill 双入口说明，并补充不同安装方式、入口差异和重复安装检查点

## v0.2.1 (2026-06-17)

### 新增

- 大任务拆解规则：内容量大的任务必须拆解成小步骤，禁止尝试一次性生成大量内容
- 拆解触发条件：生成超过 200 行的文件、包含多个独立板块的内容、需要整合大量数据或信息
- 拆解方法：先骨架后填充、按板块拆解、每步输出进度、单步内容不得超过 100 行
- 拆解示例：错误做法和正确做法对比

### 改进

- 用强制性表述替换建议类语义
- 修复“补脑”为“脑补”

## v0.2.0 (2026-06-11)

### 新增

- 深挖判定清单增加 Why 层（根本动机 + 品质层级）
- 深挖判定清单每个项目增加操作性定义
- 计划确认增加回退路径
- 工作模式增加 digraph 流程图
- 计划确认增加品质层级确认（MVP / 精打磨 / 生产级）

### 改进

- 工作模式从四阶段升级为五阶段
- 澄清阶段输出要求增加“优先闭合 Why 层”
- 计划阶段输出增加品质层级标注

## v0.1.0 (2026-05-25)

### 初始版本

- 10 条铁律定义重任务驱动约束
- 四阶段工作模式：事实收集 → 深度澄清 → 计划确认 → 连续执行
- 深度澄清规则、计划规则、执行规则、输出要求、异常处理、失控判定、成功标准
