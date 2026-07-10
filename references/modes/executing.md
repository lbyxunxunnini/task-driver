# Executing Mode

执行阶段。用于 approved plan 之后：按计划连续执行、检查分支/工作区、TDD、可选 subagent 派发、single-agent 降级、写 TaskResult/ReviewReport、更新 ledger。

执行 approved plan，不重新发明需求。按任务推进，更新 ledger，边做边验证，只在定义的停机条件下回问。

执行阶段的目标单位是整个 PlanPacket，不是单个优先级阶段、批次或小任务。只要 approved plan 中仍有 pending / in_progress 任务，且未命中停机条件，就必须继续推进下一个任务；不得在 “P0 完成”“前 5 项完成”“小目标完成” 之后询问用户是否继续。阶段性汇报只能作为进度更新，不能把继续执行责任转交给用户。

执行阶段不得降低目标。计划目标写“全部 / 完整 / 100% / 迁移 / 覆盖”时，scope_denominator 中每个目标单元都必须有执行状态、验证证据和最终路由。做了 30% 不能包装成“核心已完成”；未覆盖单元必须标为 blocked、plan-revision，或回到 brainstorming 取得用户明确降级批准。

## 执行前检查

编辑前必须：

1. 读取 approved plan 和 ledger。
2. 检查 git status 和当前分支。
3. 如果在 `main`/`master` 上做非小型修改，默认先使用隔离分支/工作区；不得直接在 `main`/`master` 推进。
   - 若环境允许安全创建分支/工作区，创建后在 ledger 记录分支/工作区名称。
   - 只有以下情况才停机回问：无法创建隔离环境、当前工作区存在未归属改动且隔离会丢失上下文、用户明确要求留在当前分支、或创建隔离环境本身有风险。
   - 用户未批准前，不得在 `main`/`master` 执行非小型写入。
4. 执行前必须建立 baseline verification。
   - 优先运行 plan 指定的 baseline verification。
   - 如果 plan 未指定，必须从项目事实中推导最小基线检查，例如测试命令、lint/analyze、build、类型检查、目标文件存在性检查或当前行为复现命令。
   - 如果确实无法运行任何基线，必须在 ledger 记录原因、影响的证据强度、替代检查方式，并在执行前停机回问是否接受无 baseline 风险。
   - 未建立 baseline 且未获用户接受风险前，不得进入写入阶段。
5. 检查 plan 是否有矛盾、缺失依赖或不可执行步骤。
   - 若矛盾来自目标、范围分母、目标原则、拆解轴、AC、质量层级、共享理解、技术方案取舍或风险边界未澄清，必须回到 brainstorming。
   - 若 spec 正确但任务顺序、文件映射、接口假设或验证命令错误，必须进入 plan-revision。
6. 确认 `PlanPacket.execution_mode`。没有明确 subagent 工具时，使用 `single-agent`。

## 多 Agent 降级

不得要求环境必须支持 subagent。

### 没有 subagent 时

使用 `single-agent`：

- 当前 agent 自己执行每个任务。
- 执行前读取 ledger 中的 PlanPacket。
- 执行后写 TaskResult。
- 另起一遍思路做 Review Gate，并写 ReviewReport。
- 最后交给 verification 阶段写 VerificationReport。

### 有 subagent 时

必须按 `PlanPacket.execution_mode` 执行：

- `multi-agent-review`：按 plan 将 Reviewer 或 Verifier 派给独立 agent；高风险、跨模块或用户要求复核的任务不得退回 single-agent，除非 subagent 工具不可用，并记录降级原因。
- `multi-agent-parallel`：只有 `PlanPacket.execution_mode` 明确允许并行，且任务文件集合不重叠、合并规则和最终验证命令已定义时才可并行派发 Implementer。
- 若执行阶段发现 `PlanPacket.execution_mode` 与当前工具能力不一致，必须更新 ledger 并触发 plan-revision 或停机回问，不得自行切换模式。不得把 `gate_mode` 当作执行形态。
- 只把相关 packet 和必要文件路径交给 subagent。
- 要求 subagent 返回 TaskResult 或 ReviewReport。
- 不接受纯散文总结作为完成证据。
- controller 保留最终责任；subagent 输出只是证据，不是权威。

## 执行循环

每个任务：

1. 在 ledger 标记 `in_progress`。
2. 按 plan 步骤执行。不得静默跳过 plan 步骤。
   - 如果步骤不可能执行，必须记录具体原因、受影响的任务/AC、已尝试的替代事实收集，并进入 `blocked` 或 `plan-revision`。
   - 如果步骤不安全，必须停止执行，说明风险类型、潜在影响和安全替代方案，并按停机回问模板让用户拍板。
   - 只有替代步骤不改变 AC、范围、风险边界和验证强度时，才可作为同任务内替代执行；替代步骤必须写入 ledger。
	   - 替代步骤改变 plan 假设时，必须触发 Plan Revision Protocol。
   - 如果执行中发现需要用户决定目标、范围、AC、质量层级、风险接受或技术方案取舍，必须停止当前任务并回到 brainstorming；不得边执行边替用户决定。
3. 行为变化走 TDD：
   - 先写失败测试。
   - 运行并确认失败原因符合预期。
   - 做最小实现。
   - 运行测试和相关回归检查。
   - 只在测试保持通过时重构。
   - 不写失败测试时，必须符合主控 TDD 例外，并在 ledger 记录豁免原因、替代验证方式和对应 AC 的 evidence_strength 上限。
4. 只有用户或 plan 要求 commit，且任务已验证，才 commit。
5. 更新 ledger：改动文件、命令、结果、commit、风险。Evidence 按结构化字段写（见 planning ledger 模板）。
6. **Scope Drift 检查**：对照 `files_changed` 与 PlanPacket 的 File Map。超出集合则停机回问，不得隐性扩 scope。
7. **Target Coverage 检查**：对照 Target Coverage Matrix 和当前任务的 Target units。目标单元未执行、未验证或证据弱于 plan 预期时，必须写入 ledger 并按 blocked / plan-revision / brainstorming 路由；不得静默移到 backlog。
8. 写 TaskResult packet，含 `task_id` (T-NNN) / `status` / `files_changed` / `commands_run` / `evidence` / `ac_coverage`。**`ac_coverage[]`** 逐项填写，`ac_id` 必须引用 SpecPacket 中的 `AC-N`；`covered` 取 `full / partial / none`；`evidence` 引用本轮 Evidence 条目。若任务声明覆盖某个目标单元，也必须在 evidence 或 deviations_from_plan 中说明该目标单元状态。
9. 做 Review Gate。
10. 写 ReviewReport packet。

完成一个任务后：

- 若 PlanPacket 仍有未完成任务，更新 ledger 后继续下一个任务。
- 若所有任务完成，立即进入 verification 阶段；验证前不得宣称完成、通过或可交付。
- 只有命中停机条件、Scope Drift、Review Gate 阻塞、2 轮执行-验证循环退出、plan-revision 或用户明确暂停时，才允许停止连续推进。

## Scope Drift Detector

触发时机：每个任务的 TaskResult 写入前，必须执行一次。

比对规则：

- 收集本轮任务实际改动的文件集合 `files_changed`。
- 取 PlanPacket.tasks[当前任务].files 与全局 File Map（Create / Modify / Test / Doc 路径）的并集，作为允许集合。
- 判断 `files_changed` 是否为允许集合的子集。
- 不一致时：在 ledger 记录超出路径、原因、必要性，停机回问用户是否扩 scope；未获批准不得推进。
- 调试临时中间产物必须优先写入系统临时目录或 plan 允许的临时路径。
- 若临时产物已出现在工作区且不在 File Map 中，必须先判断归属：
  - 确认为本轮生成且无保留价值：可删除，并在 ledger 记录路径和原因。
  - 无法确认归属或可能是用户文件：不得删除，必须停机回问。
  - 需要保留：必须触发 Scope Drift，补入 File Map 或计划修订。
- 修改 `.gitignore` 视为文件改动；若 `.gitignore` 不在 File Map 中，必须触发 Scope Drift，不得直接写入。

反例：为修一个全局错误顺手改了十幾个不在 File Map 的文件仍推进任务——违规。

## 执行-验证循环退出

同一 requirement 最多执行-验证 2 轮。每轮都要在 ledger 记录尝试内容、验证命令、结果、失败原因和下一步假设。

第 2 轮后仍未通过时，停止继续修补，并写入：

- `blocked`：需要用户决策、权限、环境、外部服务或范围调整。
- `partial`：核心目标满足但存在明确缺口，等待用户接受或拒绝。
- `plan-revision`：原 plan 假设错误，必须回到计划阶段。

不得无限重复“修一下再测一下”。

## 执行反例

本阶段反例必须读取 `references/counterexamples/executing.md`；命中任一反例时按该文件路由，不得继续推进。

## 阶段输出：TaskResult

字段以 `SKILL.md` 的结构化交接 Packet 为准；本阶段至少写入：

- `task_id`（T-NNN，引用 PlanPacket.tasks[].id）。
- `status`（pending / in_progress / done / blocked / partial）。
- `files_changed`（供 Scope Drift Detector 用）。
- `commands_run`。
- `evidence`（结构化，与 ledger Evidence 条目一致）。
- `ac_coverage[]`：列出本任务增量覆盖的 AC，每项 `{ac_id, covered, evidence}`。未覆盖任何 AC 不是错，但必须与 plan 中该任务的 acceptance_ac_ids 一致；不一致时记入 deviations_from_plan。
- `deviations_from_plan`（含任何 Scope Drift / 接口偏离 / 补充依赖）。

## Review Gate

每个 PlanPacket.tasks[] 中的任务都必须执行 Review Gate，不得以“任务太小”或“只是文档/配置/测试改动”为由跳过。

Review Gate 可按任务风险调整深度：

- 低风险文档/静态内容任务：至少检查 scope、AC 映射、文件范围和验证证据。
- 代码/配置/测试任务：必须检查 spec compliance、代码/内容质量、验证证据和未授权扩张。
- 高风险任务：必须检查安全、权限、数据、迁移、发布、依赖、构建配置、公共 API、回滚风险。

通用检查项：

- Target coverage：任务是否覆盖计划声明的目标单元；有没有把完整目标缩成核心路径。
- Spec compliance：任务验收是否满足，是否遗漏要求，是否加入未授权行为。
- Code/content quality：改动是否足够小、命名清楚、符合本地模式、无无关重构、无脆弱测试、无隐藏 TODO。
- Verification：命令输出是否新鲜，是否覆盖该任务；功能、迁移、流程或协议行为变化不得只靠文件存在、文本命中或 diff 作为完成证据。

Critical 或 Important 问题阻塞继续。必须修复并复审后进入下一个任务。

以下 finding 必须标 Critical：

- scope_denominator 中的目标单元遗漏、未计划、未执行或无验证证据。
- 目标声明是全部、完整、100% 或迁移，但实际只完成子集。
- 任务降低 AC、验证强度或目标原则，且没有用户明确批准。
- 用文件存在、文本命中、只看 diff 冒充功能级完成。

只有同时满足以下条件，finding 才可标为 Minor 并进入 ledger backlog：

- 不影响任何 AC 的 Met/Partial 判定。
- 不影响安全、权限、数据、迁移、发布、依赖、构建配置、公共 API。
- 不造成用户可见错误、主要流程退化或验证命令失败。
- 不增加后续任务的实现风险或回滚风险。
- 有明确 owner、处理建议和可接受的延期理由。

不满足任一条件时，必须标为 Important 或 Critical。

## 阶段输出：ReviewReport

字段以 `SKILL.md` 的结构化交接 Packet 为准；本阶段至少写入 task id、状态、findings、severity、file、issue、required fix。

## 停机条件

出现以下情况停下问用户：

- plan 指令不清楚或不可执行。
- 执行中暴露未澄清的目标、范围、AC、质量层级、技术方案取舍或风险边界。
- 执行中发现 scope_denominator 缺失、目标单元不可验证、目标原则与计划冲突，或需要降低完整性目标。
- 测试反复失败且根因未知。
- 修复需要扩大 scope。
- plan 要求和代码质量或安全冲突。
- 任务需要未明确批准的破坏性 git/文件操作。
- 依赖、凭据、环境或外部服务阻塞，且无安全替代路径。

不要为了总结进度而停。给简短进度更新，然后继续执行。

禁止把阶段性完成当成停机条件。错误示例：`P0 阶段全部完成，当前进度 5/25，下一步进入 P1，是否继续？`。正确做法：记录 P0 证据和 ledger 状态，然后自动执行 P1 的第一个 pending task。

## 恢复规则

上下文压缩或会话恢复时：

1. 先读 ledger。
2. 相信 ledger 和 git history，优先于记忆。
3. 从第一个未完成任务恢复。
4. 继续前检查工作区状态。

## 完成移交

所有 plan 任务完成后，进入 `verification` 阶段。验证前不得宣称完成；最终验证和用户验收门前不得要求用户决定是否继续执行已批准计划。
