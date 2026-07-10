# Changelog

## v0.8.2 (2026-07-10)

### 改进

- **会话状态维持**：Task Driver 一旦触发，在任务完成（`accepted_by_user`）或用户显式取消前，所有后续用户消息都必须按框架处理，无需重复触发词。退出条件明确：只有用户显式取消或任务完成验收通过时，才允许退出框架。禁止以"没有触发词"、"任务简单"等理由静默退出。
- **范围锚定（防止目标漂移）**：扩展范围锚定规则，涵盖外部样本和上下文信息两种场景。
  - **外部样本**：当任务涉及外部产物（demo、测试样本、参考实现等）时，严格区分优化目标和参考样本。参考样本仅用于提供上下文、灵感或对比基准，不得成为修改目标。发现样本问题时记录但不修复，修复请求必须由用户显式发起。
  - **上下文信息**：用户提供的日志、错误信息、输出结果、截图等，是为当前任务服务的上下文信息，不得被理解为"新的场景"或"新的任务目标"。
- **违规处理**：若 agent 把上下文信息误解为新的任务场景，或被外部样本问题吸引偏离原始目标，必须立即回退到目标定义阶段重新澄清范围。

## v0.8.1 (2026-07-10)

### 改进

- **启动预检门**：显式触发后，首次写入前必须声明当前阶段、目标草案、是否有 approved spec/plan。
- **写入屏障**：没有 approved spec 且没有 approved plan 时，禁止一切写入动作（含 mkdir、apply_patch、安装依赖、git 操作）。spec/plan 产出阶段豁免，但产出后必须等用户确认。
- **优先级声明**：显式触发时，Task Driver 协议优先于 agent 的默认自动执行行为；读取协议不等于授权执行。
- **小任务内联时序**：明确内联 spec/plan 属于目标定义动作，不受屏障约束，但必须等用户确认后才能执行写入。
- **反例补全**：新增"读完协议后直接执行""口头计划替代已确认计划""预热创建工件目录""未确认 spec/plan 就创建工件目录或文件"4 条反例。
- **软性话术硬化**：修复 15 条建议型/允许绕过型/条件模糊型话术（由 agent 判断 → 必须回退；可选 → 必须记录；默认 → 必须；应 → 必须；除非 → 删除口子）。

### 修复

- **消除小任务与写入屏障的逻辑冲突**：拆分屏障的两个阶段——目标定义（产出 spec/plan）和执行（写入代码/文件），明确时序规则。

## v0.8.0 (2026-07-10)

### 改进

- **产物路径改为 `.task-driver/`**：spec、plan、ledger 统一使用 `.task-driver/{specs,plans,ledgers}/YYYYMMDD-HHmm-主题.md`，并同步 `.gitignore`、模板、示例和契约检查脚本。
- **精准目标门禁**：Target 新增 `scope_denominator` 和 `target_principles`，要求“全部 / 完整 / 100% / 迁移 / 覆盖”类目标先定义可计数分母和取舍原则。
- **拆解深度门禁**：Planning 新增 Target Coverage Matrix 和 Decomposition Strategy，禁止用 Phase、文件列表或产物名替代可执行任务。
- **功能级检验门禁**：文件存在、文本命中、只看 diff 默认降为 weak evidence；新增功能、迁移、流程和协议优化必须用功能级验证或反例样例证明。
- **自检优化循环**：验收前自检升级为发现、修复、复验、记录证据的循环，VerificationReport 自检增加 Target coverage 和 Self-test improve loop。

### 修复

- **数据收集展示降噪**：`grilling_state` 默认只向用户展示当前决策摘要，完整表格写入 ledger，避免把内部状态表格每轮暴露给用户。
- **反偷懒反例补强**：新增目标空泛就开工、百分比目标无分母、Phase 包装成任务、30% 冒充 100%、弱证据包装完成、自检假闭环等反例。

## v0.7.0 (2026-07-07)

### 改进

- **术语表改为 JSON 格式**：`references/glossary.md` 改为 `references/glossary.json`，减少文件体积，便于程序解析。
- **统一术语展示规则**：所有面向用户的英文术语（无论是否在 glossary 中有映射）都必须使用 `中文[英文]` 格式。
- **Packet 展示富文本化**：新增"面向用户展示规则"，明确 SpecPacket、PlanPacket、TaskResult、ReviewReport、VerificationReport 展示时必须转换字段名和枚举值。
- **新增反例**：新增"未映射术语裸用英文"和"Packet 展示裸用字段名"两类反例。

### 修复

- **grilling_state 展示**：从原始 YAML 改为富文本表格格式，同时保留机器契约 YAML 用于写入 ledger。
- **Decision Trace 表头**：统一使用 `中文[英文]` 格式（如 `层级[layer]`、`决策点[decision_point]`）。
- **Grilling Summary 字段**：统一使用 `中文[英文]` 格式（如 `共享理解[shared_understanding]`）。
- **Design Tree Coverage 表头**：统一使用 `中文[英文]` 格式。

## v0.6.3 (2026-07-07)

### 新增

- **契约一致性检查脚本**：新增 `scripts/check-contracts.sh`，检查 packet 字段、禁用表达、质量层级枚举、证据强度规则和三条黄金路径示例，防止 `PlanPacket.mode`、`medium 可标 Met` 等契约漂移再次出现。
- **Packet 最小模板**：新增 `references/packet-templates.md`，提供 SpecPacket、PlanPacket、TaskResult、ReviewReport、VerificationReport 的最小合法 YAML 模板，降低手写 packet 的错误率。
- **30 秒快速入口**：新增 `references/quick-start.md`，用决策树判断是否启用 Task Driver，并给出 gate_mode / execution_mode 选择规则。
- **三条黄金路径**：新增 `references/walkthroughs/lite.md`、`standard.md`、`strict.md`，分别覆盖低风险小任务、默认跨文件 bugfix、高风险权限/发布任务。
- **发布前自测清单**：新增 `references/self-test-checklist.md`，明确发布前必须运行的命令和人工门禁。

### 改进

- **README 入口收敛**：补充 quick-start、packet templates、self-test checklist、三条 walkthrough 和 `scripts/check-contracts.sh` 的目录说明与使用入口。
- **协议索引扩展**：`SKILL.md` 的引用表新增 quick-start、packet-templates、self-test-checklist 和分模式 walkthrough 的加载时机。

### 修复

- **设计树覆盖门禁**：brainstorming 新增 Design Tree Coverage，要求目标、范围、行为、方案、验证、风险分支都标记为 decided / deferred / out_of_scope，不得带 open 分支进入 planning。
- **宏观到细分拷问加强**：每层闭合前必须完成上游依赖、横向分支和下游影响三项检查，防止只问主路径或浅闭合宏观问题。
- **拷问反例补强**：新增“只问主路径”“宏观问题浅闭合”“同层替代路径未处理”“Design Tree Coverage 缺失”“设计树仍有 open 分支”等反例。
- **目标驱动状态机**：新增 Target -> brainstorming -> planning -> executing -> verification -> User Acceptance Gate -> accepted_by_user 的正常状态链，明确目标定义和回路条件。
- **跳过阶段记录**：任何阶段跳过必须记录 skipped_stage、reason、risk、replacement_evidence 和 user_approval；否则视为协议违规。
- **回路规则强化**：planning / executing 发现未澄清目标、范围、AC、技术取舍或风险边界时必须回到 brainstorming；verification 按失败性质回到 executing、planning 或 brainstorming。
- **验收前自检门**：User Acceptance Gate 前新增 Pre-Acceptance Self-Check，必须逐项检查 Plan tasks、Review reports、AC coverage、Verification strategy、Scope drift、Quality gate 和 Residual risk。
- **VerificationReport 入包**：新增 `pre_acceptance_self_check` 必填字段；没有自检结果或自检存在 fail 时，不得进入 `awaiting_user_acceptance`。
- **反例补强**：新增“未自检就请求用户验收”和“用户提醒后才自检”反例，防止把自检责任转交给用户。
- **Grilling State 状态机**：brainstorming 新增当前分支、当前问题、上游依赖、推荐答案、用户决策、未闭合分支和 shared_understanding 状态，防止事后补表式伪拷问。
- **事实与决策分离**：明确可从代码库、文档、日志、git 或已有工件查到的事实必须由 agent 自查；目标、优先级、范围、风险和方案取舍才交给用户决策。
- **Shared Understanding Gate**：spec 标为 Approved 前必须输出共享理解摘要，并获得用户对目标、范围、非目标、关键取舍、验证方式和风险的明确确认。
- **Grilling Summary 入包**：SpecPacket 新增 `grilling_summary`，planning 必须检查 `shared_understanding: true` 才能继续。
- **拷问细化协议**：新增宏观到细节的 6 层拷问链：整体目标、大类/规划轴、范围切片、小项目/模块、行为细节、实现约束。
- **Decision Trace 强制化**：Spec 模板和 SpecPacket 新增决策轨迹，记录每层决策点、选项、用户/assumption 决策及其对范围、验收、风险和验证的影响。
- **计划前置门禁收紧**：Planning 阶段必须检查 Decision Trace；技术任务必须能追溯到 Decision Trace、AC 或 Constraints，否则回到 brainstorming。
- **反例补强**：新增“拷问跳层”“用户笼统回答后伪闭合”“没有 Decision Trace 就写计划”三类反例。
- **澄清话术自然化**：禁止把“只需要你拍板 1 个问题”作为固定标题，模板改为直接的“请确认”，仅允许最终收口问题使用类似表达。
- **技术方案分叉前置闭合**：会改变接口、依赖、验证方式、回滚方式、用户流程或风险边界的技术方案必须回到需求澄清阶段逐层确认，不能直接进入计划或执行。
- **计划目标和验证方案补强**：Plan 模板新增 `Success Definition` 和 `Verification Strategy`，防止只有任务清单、没有整体目标和最终验证路线。
- **整体计划连续推进**：用户确认计划后，执行阶段必须推进整个 PlanPacket；优先级阶段、批次、小目标或子任务完成后不得询问“是否继续”。

## v0.6.2 (2026-07-06)

### 改进

- **术语表提升为启动级门禁**：`references/glossary.md` 从按需 P2 提升为首次用户可见阶段/协议/状态/字段/模式说明前的 P0 必读，覆盖中间进度更新、阶段切换、停机回问和最终报告。
- **全局反例加严**：新增阶段进度说明裸用英文阶段名、解释协议前未读术语表、误把机器契约中文化三类反例，直接覆盖 `brainstorming` / `planning` / `executing` / `verification` 裸输出问题。
- **README 术语格式同步**：统一使用 `中文显示名[英文标识]`，并补充全局反例文件的读取说明。

## v0.6.1 (2026-07-03)

### 新增

- **分级执行模式**：新增 `strict[严格]` / `standard[标准]` / `lite[轻量]` 三种模式，解决"简单任务流程过重"的核心矛盾。Lite 模式对 Review Gate、质量评分、证据强度等门禁按风险放宽，但仍保留 spec/plan/ledger 结构。
- **断点续传协议**：新增 `references/resume-protocol.md`，定义 Checkpoint 格式、恢复判定规则和预检门禁。中断后重新触发时，agent 自动读取 ledger 判定是否可从断点续传。
- **自动重试机制**：定义可恢复错误白名单（lint-fix / test-flaky / file-lock / network-retry），每种错误自动重试 1 次后升级。安全/权限/数据/发布相关错误不适用自动重试。
- **端到端使用案例**：新增 `references/walkthrough.md`，用一个完整的 CLI --verbose flag 任务演示从触发到交付的全流程。
- **FAQ**：新增 `references/faq.md`，从 counterexamples 提炼常见问题，按触发、澄清、执行、多 Agent、质量验收、术语分类。
- **错误自分类**：每个错误模板新增 `auto_recovery[自动恢复]` 级别（retryable / escalate / block），定义 agent 首次响应策略。

### 改进

- 根 `SKILL.md` 协议参考表新增 resume-protocol（P1）、faq（P2）、walkthrough（P2）的读取优先级。
- README 治理门禁新增执行模式和断点续传说明。
- 错误模板新增自动恢复级别标注。
- 重写 `SKILL.md` summary，面向 C 端用户强调三级门禁和可恢复特性。

## v0.5.1 (2026-07-03)

### 改进

- **glossary 中英文输出规范统一**：格式说明从 `中文（英文）` 改为 `中文[英文]`；补全 correctness、completeness、robustness、maintainability、usability、overall 六条质量维度中文映射。
- **verification 审计表模板中文化**：完成审计表表头及状态值统一使用 `中文[英文]` 格式。
- **全局反例门禁**：新增 `references/counterexamples/global.md`，面向用户输出使用英文原值视为协议违规；glossary 未收录术语由 agent 自行翻译后输出。

## v0.5.0 (2026-07-03)

### 改进

- **阶段反例门禁拆分**：新增 `references/counterexamples/`，按 brainstorming、planning、executing、verification 拆分反例文件。
- **根入口轻量索引**：根 `SKILL.md` 的反例门禁改为强制读取对应阶段反例文件，避免主入口继续膨胀。
- **长协议拆分**：新增 `references/glossary.md`、`references/packet-contract.md`、`references/runtime-protocols.md`，将术语表、Packet schema、状态机、证据强度、TDD 例外和循环协议移出根入口。
- **质量评分闭环**：新增 `references/quality-rubric.md`，为 verification 阶段补充 1-5 质量评分、质量层级阈值和 improve loop。
- **读取优先级**：根 `SKILL.md` 将 references 加载规则升级为 P0/P1/P2 优先级，减少每次任务全量读取协议文件的 token 成本。
- **领域 skill 协作**：新增领域 skill 协作规则，明确 Task Driver 负责流程治理，领域 skill 输出必须回填 TaskResult、ReviewReport 或 VerificationReport。
- **触发词显式化**：frontmatter 与 SkillHub description 明确写入 `tdr-`、`task-driver`、`/task-driver` 的开头触发规则。
- **README 同步**：说明反例门禁文件位置、按阶段加载方式、运行时工件忽略建议和最短流程 walkthrough。

## v0.4.8 (2026-07-03)

### 破坏性变更

- **移除插件/多 skill 双入口**：删除 `.codex-plugin/plugin.json` 和 `skills/` 多 skill 目录，不再发布 Codex 插件形态。
- **根入口恢复为 `task-driver`**：根 `SKILL.md` 从 `task-driver-standalone` 改为唯一入口 `task-driver`，安装后只暴露一个 skill。
- **阶段收敛为内部模式**：`task-driver-brainstorming`、`task-driver-planning`、`task-driver-executing`、`task-driver-verification` 不再作为独立 skill 暴露，改为 `references/modes/` 下的内部阶段参考文档。

### 改进

- **ccswitch/SkillHub 友好发布结构**：新增 `.skillhub.json` 和 `VERSION`，目录结构对齐 `flutter-forge` 这类单 skill 完整包。
- **根控制器完整化**：根 `SKILL.md` 直接包含完整 Task Driver 控制器协议，不再要求读取 `skills/task-driver/SKILL.md` 才能获得完整契约。
- **README 单模式化**：安装说明收敛为“安装整个目录，只看到一个 `task-driver` 入口”，避免 standalone / plugin / 阶段 skill 混淆。

## v0.4.6 (2026-07-02)

### 改进

- **单问题澄清门**：主控、根入口和 brainstorming 阶段新增硬约束：禁止问卷式连续提 1 个以上问题；每轮只能问一个最高影响用户决策点。
- **推荐答案强制化**：澄清问题必须尽量给 2-3 个互斥选项和推荐答案，禁止只抛开放问题。
- **重新规划澄清顺序**：用户要求重新规划、整体规划、重构规划、从头梳理或重新设计时，必须先从整体规划视角或大类划分开始，不得直接跳到文件、接口、页面等实现细节。
- **按需补充 N/A 门禁**：User scenario / Risks / Trade-offs / Alternatives 只有经事实收集和影响判断确认不影响方案或验收时，才可标 `N/A`。
- **参考答案逃逸收紧**：能给参考答案时不得借口不能给而退回开放式提问；只有用户独占事实类问题可不给选项，并必须说明原因。
- **默认值使用收紧**：默认值仅允许用于低风险、可逆、行业惯例明确且不影响目标/范围/验收的细节；影响 spec、plan、AC 或风险边界时必须回到单问题澄清。
- **第一片拆分标准**：任务过大时先识别任务类型；重新规划类任务的第一片必须是规划框架片，功能/bugfix 类任务的第一片必须覆盖可验证端到端价值或最小复现闭环。
- **小任务内联收紧**：内联 spec/plan 必须满足一轮完成、最多一个非关键文件、无高风险行为且有明确验证；单文件高风险变更也必须走完整 spec/plan/ledger。
- **质量层级降级白名单**：未指定质量层级时默认精打磨；只有诊断、探索、一次性脚本或临时数据整理且无生产风险时才可降为 MVP，并必须记录降级原因和不覆盖边界。
- **阶段 skill 降级可追踪**：阶段 skill 不可用时必须记录 `mode: degraded-single-skill`、不可用阶段和原因，补齐所有必需 packet，并在最终报告披露降级及证据影响。
- **Plan Revision 判定硬化**：只有 Goal、Scope、AC、Constraints、Quality level 和风险边界均不变时，才可仅升级 plan；否则必须回到 brainstorming 重写 spec。
- **执行模式选择硬化**：PlanPacket.mode 必须记录选择理由；有 subagent 且任务高风险、跨模块或用户要求复核时必须优先 multi-agent-review；并行模式仅在文件不重叠且合并/验证规则明确时允许。
- **main/master 写入隔离优先**：在 `main`/`master` 上做非小型修改时默认先使用隔离分支/工作区；只有隔离不可行、会丢失上下文、用户要求留在当前分支或隔离本身有风险时才回问。
- **baseline verification 必建**：执行前必须建立 baseline；plan 未指定时从项目事实推导最小检查，确实无法建立时需记录原因、证据影响和替代检查，并经用户接受风险后才可写入。
- **Plan 步骤异常受控**：不得静默跳过 plan 步骤；步骤不可能时进入 blocked 或 plan-revision，步骤不安全时停机回问，替代步骤必须不改变 AC、范围、风险边界和验证强度并写入 ledger。
- **Executing subagent 模式对齐**：执行阶段有 subagent 时必须按 PlanPacket.mode 执行；高风险/跨模块/用户要求复核任务不得自行退回 single-agent，工具能力不一致时必须记录并触发 plan-revision 或停机回问。
- **Minor finding 白名单**：只有不影响 AC、安全/权限/数据等高风险面、用户可见行为、验证命令和后续风险，且有 owner、处理建议和延期理由时，finding 才可标 Minor 进入 backlog。
- **TaskResult.ac_coverage 必填**：主 schema 将 `ac_coverage` 改为 required；每个任务必须列出 plan 中 acceptance_ac_ids 的覆盖情况，未覆盖也必须写 `covered: none` 和原因。
- **VerificationReport 用户验收状态必填**：`delivery_acknowledged_by_user` 改为 required；初次写入必须为 `pending`，用户回复后更新为 `true / false / partial`。
- **Partial 验收门收紧**：medium 证据只能标 Partial，并必须写 caveat、缺口、影响范围和补强验证命令；Partial 只有在核心目标有证据且未覆盖部分不涉及高风险面时才可进入 User Acceptance Gate。
- **验证命令跳过受控**：plan 验证命令必须运行；确实无法运行时必须记录命令、原因分类、诊断、替代证据和 AC 影响，未运行原命令的 AC 不得标 Met，无替代验证必须 Blocked。
- **验证失败路由分类**：验证失败后不得默认回 executing，必须先分类为 executing / blocked / partial / plan-revision / brainstorming，并写入 Iteration Log 的 `next_assumption` 和 `outcome`。
- **Partial-accept 残余项路由收紧**：partial-accept 后残余项只有在用户明确接受且不影响已接受 AC、高风险面或主要流程时才可进 backlog；否则必须进入 plan-revision 或 blocked。
- **重新规划 v1 差异说明**：首版 plan 仍可省略 `Diff From v[N-1]`，但重新规划、重构规划或替代方案类 v1 必须新增 `Change From Current State`，说明相对现状的结构变化、保留项、废弃项和迁移风险。
- **TDD 例外白名单**：功能、bugfix、行为变化默认必须先写失败测试；只有明确豁免、纯非行为变更、无可运行测试框架且无法安全补充，或只能人工/外部系统验收时才可跳过，并必须记录替代验证和证据强度上限。
- **Review Gate 全任务覆盖**：每个 PlanPacket task 都必须执行 Review Gate，不得因任务小或仅文档/配置/测试改动跳过；只允许按风险调整 review 深度。
- **最终报告交付路径结构化**：最终报告必须输出 `delivery_acknowledged_by_user` 状态，并按 accepted / awaiting_user_acceptance / partial / rejected_by_user-or-blocked 判定交付路径和 next_action。
- **Spec 生成路径澄清**：brainstorming 不只问会改变 spec 的问题；重新规划类任务的规划视角、大类划分、范围切片和优先级都视为 spec 生成路径问题，必须逐层闭合。
- **Planning 信息缺口分类**：planning 阶段缺信息时必须先分类；项目事实继续查，spec 缺口回 brainstorming，用户决策/外部权限才按单问题澄清门回问，禁止一次列多个 planning 问题。
- **Planning 事实收集细化**：计划阶段不得只读目录结构，必须检查项目规则、代码结构、依赖脚本、现有任务资产、git 状态和当前行为/失败证据，以支撑可执行 plan。
- **根入口降级同步**：standalone 根入口无法加载子 skill 时必须视为 `mode: degraded-single-skill`，记录不可用阶段、补齐全部 packet、写入 ledger，并在最终报告披露降级和证据影响。
- **Plan assumption 结构化**：planning 阶段的细节假设必须使用 `ASM-N`，记录内容、依据、验证点、失效处理和影响范围；执行中发现假设失效必须停机并按路由处理。
- **临时产物处理收紧**：调试中间产物优先写入临时目录；工作区内计划外产物必须先判归属，无法确认不得删除，需保留则触发 Scope Drift；`.gitignore` 修改也视为文件改动。
- **Review deferred 收紧**：Critical finding 不得 deferred；Important 只有不影响 AC、高风险面和主要流程时才可由用户明确 deferred，并会将相关 AC 最高限制为 Partial。
- **Verification 失败状态对齐**：验证失败后必须按 executing / blocked / partial / plan-revision / brainstorming 分类选择下一状态；不得使用“调试”作为状态，调试动作必须归入 executing 并受 2 轮上限约束。
- **SpecPacket 持久化交接**：brainstorming 必须持久化 SpecPacket；ledger 已存在则写 ledger，未创建则写入 spec `## SpecPacket` 或 planning handoff，并在 planning 创建 ledger 时同步复制。
- **主控 Review Gate 同步**：主控流程同步为每个 PlanPacket task 必须执行 Review Gate，可按风险调整深度但不得跳过。
- **Schema 状态一致性修复**：`degraded-single-skill` 纳入 PlanPacket/VerificationReport mode 枚举；planning 明确内联 spec 输入也必须先持久化 SpecPacket；用户 reject 对应新增 `rejected_by_user` 状态。
- **双机制入口同步**：standalone 根入口明确只加载根 `SKILL.md` 时只能执行 minimal protocol，不得声称完整 Task Driver；插件 manifest 版本同步到 `0.4.6`。
- **主控模板精简**：将错误提示完整模板下沉到 `.task-driver/error-templates.md`，主控仅保留强制使用规则和适用关系索引。
- **中文显示名规范**：主控新增 98 项中英文对照表；面向用户输出时使用“中文显示名（英文标识）”，同时保留字段名、枚举值、路径、JSON/YAML key 等机器契约原值。
- **版本同步**：根入口、插件 manifest、README 和发布说明同步到 `0.4.6`。

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
  - `.task-driver/specs/YYYYMMDD-HHmm-主题.md`
  - `.task-driver/plans/YYYYMMDD-HHmm-主题.md`
  - `.task-driver/ledgers/YYYYMMDD-HHmm-主题.md`
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
