# Changelog

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
