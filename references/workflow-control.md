# 轻量状态检查

主控在对话或[唯一任务摘要](state-recovery.md#何时建立记录)中维护原目标、当前环节、已决定事项及来源、未决事项、下一动作和授权。普通讨论在上下文维护状态；达到[记录条件](state-recovery.md#何时建立记录)后，建立或复用同一任务摘要并增量维护问题和回答。不要为了检查重新询问已确定的事项或制造新问题。

## 强制入口与失败关闭

`workflow_control.py` 是主控的结构检查器，不是另一个流程源。主控每完成一个阶段结果、准备提问、展示计划/目标、启动子代理或开始执行前，必须调用 `next` 并执行返回动作；讨论最终回复必须调用 `final`。准备业务执行时还必须调用 `begin`，取得 `execution_receipt` 后才能启动第一项。

脚本只读标准输入或指定 JSON，不创建、覆盖或更新任务记录。例如 `next --state -` 从标准输入读取状态；`begin` 只返回一次性结构回执；`final` 从 `{"state":{...},"draft_reply":"最终回复草稿","discussion_handoff":{...}}` 读取状态、正文和唯一交接对象；`check` 只检查结构。

脚本未运行、执行失败、输入不完整或结果无法解析时，只能停在本阶段：不得继续业务写入、启动执行子代理、创建交付产物或把字段自填为已通过。讨论和只读调查可在明确说明后人工核对；业务执行没有人工继续通道。

状态包含 `task_id`、`phase`、`status`、`next_action`、`decisions`、`plan`、`coverage_checked`、`plan_requested` 和 `gates`；执行前还须填写 `goals`。决定项记录稳定 `id`、主题 `subject`、`status`、实际决定 `value` 和 `source`；`decided`、`delegated` 均须有实际决定，已获委托但尚未决定时仍记 `pending` 并保留委托来源，由模型落实；待定项不需要 `value`。计划与目标各自的 `presented` 和 `evidence` 来自对话中实际可见的内容；计划和目标首次同轮正式展示时必须共享同一个 `presentation_id`，局部调整时分别保留原展示与增量展示的可追溯引用，未展示完整原文不能把增量当作首次完整展示；不由脚本自行判断消息是否送达。`goals` 可在展示前省略，进入执行时须为 `{"presented":true,"evidence":"实际目标展示来源","presentation_id":"计划展示消息"}`；`goals.presented:true` 时 `plan.presented` 必须已经为真，不能只展示目标或把两者拆成不同轮次；只有 `plan_required:false` 且 `plan_waiver_source` 记录“已有结果满足任务”的收口例外可以没有计划展示。`plan.presented:false` 且目标已展示属于结构错误，先回到计划展示。计划请求和授权分别保留来源。`plan_requested` 表示当前须交付计划：用户请求计划，或用户要求直接进入执行且讨论已闭合时仍先进入计划阶段；后一种情况的来源如实指向直接执行请求，不把它写成用户主动要求计划或内容确认。讨论尚未闭合时先处理必要事项。`plan_required:false` 仅用于无需进入正式计划阶段的收口（如已有结果满足任务），不能用于跳过计划。`plan_request_source` 使用能唯一标识该次请求的实际消息引用。同一请求的草案已交付时，`plan.draft_for_request` 填完全相同的请求引用；若有依据确认旧草案不对应当前请求，`plan.draft_not_for_request` 填当前请求引用，即使旧请求的来源无法恢复也不编造。新草案实际交付后同步更新草案证据和 `draft_for_request`，清除对应的 `draft_not_for_request`；不能提前记录交付。不同引用可能只是不同写法，未确认关系时脚本返回 `verify_plan_request`，先核对对话再更新，不推定已送达或重复提问；确实无法判断时保留未知，不假称核实。用户只回答一部分时，只更新实际覆盖的决定。填写状态前先查对话和材料，无法恢复的事实标为未知，不猜测。`discussion_question_waiver_source` 仅在用户明确暂停、明确做本轮局部并完成交付，或任务结束时填写实际消息来源；`scope_limited:true` 且 `scope_limited_source` 记录用户明确限定本轮只交付指定内容的原话和范围。目标变化时，`superseded_goals` 保存旧目标原文、`host_id`、新范围来源和 `superseded_by`；`host_goal_sync` 记录 `synced`、`stale` 或 `unavailable`，不能把旧目标伪标为当前目标。工具等待和外部阻塞不能使用这些豁免。

编号计划使用 `plan.steps`：每项必须有稳定 `id`、`action` 和 `status`，状态只能是 `pending`、`in_progress`、`done`、`blocked`；`done` 必须有实际证据，`blocked` 必须说明原因。步骤顺序不可通过重排改变；只能按列表顺序推进，一个计划最多一个进行中步骤，前项未完成时后项不能 done、in_progress 或 blocked，完成收口时默认全部步骤必须 done。

全部步骤 done 时，`next` 返回 `steps_complete`；主控只能进入验证与审查，不能继续用 `next_action` 做未列入计划的新业务动作。

业务执行入口还必须有 `analysis_complete`、`analysis_evidence`、`discussion_closed`、`discussion_closure_source`、`execution_scope`、`execution_begun` 和 `execution_receipt`。`execution_scope` 记录 `allowed_paths`、`allowed_actions` 和授权来源；`allowed_actions` 必须精确覆盖所有 `plan.steps.action`。`execution_receipt` 必须等于当前结构授权哈希。目标、计划、执行范围、子代理设置或目标跟踪方式变化时旧回执失效，必须重新运行 `begin`；`begin` 还需要相应 `previous` 状态。

计划步骤新增、删除、重排或动作变化时必须记录 `plan_revision_source`；已开始执行后改变范围或目标跟踪方式时必须记录 `execution_reset_source` 并把 `execution_begun` 恢复为 false，随后重新 begin。

`local_only:true` 只在执行阶段还需要 `local_only_source`，保存用户明确限定本轮局部任务的实际来源；没有来源不能作为绕过步骤和完成门的路径。

分析阶段只返回 `continue_analysis`，不得把 `next_action` 写成业务写入；执行前使用 `local_only` 时必须另有 `local_only_source` 和 `local_only_read_only:true`。

目标跟踪由 `goal_tracking_mode`、`goal_tracking_source`、`goal_tracking_confirmation_source` 记录。`host` 模式必须有真实 `goal_tracking_host_id` 和 `goal_tracking_host_receipt`；`plan` 或 `conversation` 模式必须有稳定的 `goals.local_goal_id`、`goal_tracking_fallback_reason`、`goal_tracking_fallback_evidence` 和用户确认来源；`unavailable` 不得进入执行。展示并确认验收目标不等于创建宿主 Goal。host 模式按真实工具类型保存 `goal_tracking_host_kind: aggregate | task_list`，不从返回条数推断。另存 `goal_tracking_host_readback`，格式如 `[{"host_id":"实际 ID","objective":"G1：已确认的通过条件"}]`。取实际创建返回或查询结果；任务列表中 host_id 各不相同，原 goal_tracking_host_id 对应其中一个。脚本校验正文与 included 一一对应，不鉴定来源真伪。旧状态缺该字段时从真实回执补录，勿自己补写或因补录重建目标；有替代记录的旧宿主不能同步时，已执行后的只读验证、审查（`read_only:true`）及业务收尾可以按新范围继续，不放行新的业务执行。范围变化致旧 execution_receipt 与当前范围不同，保留原 begin 状态的授权载荷（按脚本 execution_authorization_payload 取值）为 prior_execution_authorization；只读收尾核对原任务及原回执哈希，不能用它开始、恢复写入或分派。列表中仅对有替代记录且旧正文匹配的宿主任务例外，在该旧条目记录 `replacement_goal_ids` 指向取代它的当前验收项（纯删除为空列表），其余任务仍须逐项匹配。

等待用户或工具期间，`independent_action` 只在 `independent_action_read_only:true` 且动作精确列入 `read_only_scope.allowed_actions` 时允许；否则必须先满足完整执行入口和有效 receipt，并且动作必须精确列入 `execution_scope.allowed_actions`。

验证或审查阶段若 `execution_occurred:false`，必须显式设置 `read_only:true`；没有该标记时，按未完成执行入口处理，不能借已有结果直接写报告或业务产物。

补充状态约束：用户明确暂停、明确只做本轮局部且完成交付，或任务结束时，`discussion_question_waiver_source` 记录实际消息来源；`scope_limited:true` 时由 `scope_limited_source` 记录本轮限定原话和范围。目标变化时，`superseded_goals` 保存旧目标原文、`host_id`、新范围来源和 `superseded_by`；`host_goal_sync` 记录 `synced`、`stale` 或 `unavailable`，不能把旧目标伪标为当前目标。`goals` 保留当前有效目标；旧目标只进入 `superseded_goals`，完成时可以同时报告业务已验收和宿主目标 `stale/unavailable`。

无 Goal 模式时，`superseded_goals` 的 `host_id` 可以为空或为 `null`，但必须提供稳定的 `local_goal_id`；当前 `goals` 也记录同名 `local_goal_id`。有宿主目标时优先保留 `host_id`，不得伪造宿主 ID。

`host_goal_sync` 为 `synced` 或 `stale` 时必须仍有非空宿主 `host_id`；纯本地目标或没有 Goal 模式时只能使用 `None` 或 `unavailable`，不能声称宿主目标已同步。

目标展示时，`goals.included` 只能包含 `kind:changed`（改动直接结果）或 `kind:associated`（直接关联结果），每项必须有 `id`、`criterion` 和 `source`；`goals.excluded` 每项必须有 `id`、`item` 和用户 `source`；`goals.evidence_map` 按 included 的 id 保存非空证据引用列表。进入完成前，脚本要求每个 included 都有证据，excluded 或未知 id 不能出现在 evidence_map；脚本只校验结构和覆盖关系，不判断证据是否真实支持目标。

`goal_scope_baseline` 保存最后一次已确认目标的 included/excluded 快照。初次展示时与当前目标一致；目标临时 `presented:false` 时保留旧快照；用户变更范围并取得来源、记录 `superseded_goals` 后，更新为新范围。目标展示后进入执行、验证、审查或完成时必须提供 `previous`，用于核对当前范围与上一快照。

完成时默认 `completion_basis:evidence`；用户明确要求结束但仍有未验证 included 时，使用 `completion_basis:user_requested`，填写 `completion_request_source` 和 `completion_report`（`verified_goal_ids`、`unverified_goal_ids`），并在 `unverified_goals` 中逐项记录 `id`、`item`、`reason` 和 `impact`；若仍有未完成步骤，还必须在 `unverified_plan_steps` 中逐项记录未完成步骤的 `id`、`action`、`reason` 和 `impact`，同时如实报告“业务已按用户要求收口”和仍未验证的内容。用户要求变更目标时，不得直接沿用旧目标完成；先更新 included/excluded、记录新目标来源并保留 `superseded_goals`。旧目标缺少新字段时先迁移目标结构，脚本返回 `repair_state`，不得省略 goals 后完成。

以下是结构示意，必须按实际对话填写，不把示例当作已有决定：

`gates.execution` 记录执行范围的依据，`gates.subagents` 记录用户明确选择开启、不启用、限定用途，或明确委托模型决定子代理设置的消息来源。旧状态缺少该字段时先从可用对话或记录补查，不从执行授权推定；仍无法确认时保持缺失，执行前按主控询问。只读核实运行中或结果未知的原操作不因缺少这两项依据受阻；脚本不能验证来源内容是否真实支持设置。

```json
{"task_id":"当前任务","phase":"analysis","status":"continue","next_action":"分析当前请求","decisions":[],"plan":{"presented":false},"coverage_checked":false,"plan_requested":false,"gates":{"plan":null,"goals":null,"execution":null,"subagents":null}}
```

讨论阶段最终回复示例（`semantic_review` 只表示语义复核契约已填写，不证明复核者真的独立或判断正确）：

```json
{"state":{"task_id":"当前任务","phase":"discussion","status":"continue","next_action":"询问当前必要事项","decisions":[{"id":"D1","subject":"当前取舍","status":"pending","question":"当前取舍上你希望采用方案 A，还是方案 B？"}],"plan":{"presented":false},"coverage_checked":true,"plan_requested":false,"gates":{"plan":null,"goals":null,"execution":null,"subagents":null}},"draft_reply":"分析结果如下。\n\n当前取舍上你希望采用方案 A，还是方案 B？","discussion_handoff":{"kind":"decision","decision_id":"D1","semantic_review":{"reviewer":"main","status":"pass","target":"decision","decision_id":"D1","source":"主控按当前对话复核","checks":{"target_is_current":true,"not_already_decided":true,"not_delegated":true,"answerable_now":true,"single_question":true,"no_trailing_content":true}}}}
```

`discussion_handoff.kind` 只能是：

- `decision`：存在阻塞计划的 `pending` 决定，该决定必须填写 `question`，`decision_id` 必须对应其中一项；正文问题通过 `semantic_review` 证明它对应这个问题，不再要求逐字复制 `question`。待决项没有显式问题、语义复核目标不一致或复核未通过均失败。当 `next` 返回 `present_incomplete_plan`，或计划请求仍有缺口时，正文还必须交付绑定当前 `plan_request_source` 的缺口草案，并让语义复核填写 `incomplete_plan_delivered:true`；只问问题不交付草案不算完成计划请求。
- `plan_transition`：没有阻塞计划的待决项，`next` 必须已返回 `request_plan_transition`，正式计划尚未展示；最后问题必须表达结束讨论并开始展示正式计划和目标，推荐使用“是否结束讨论并开始展示正式计划与目标？”但措辞可以自然变化。是否真的表达过渡由语义复核判断。
- `waived`：仅用户明确暂停、明确限定本轮只交付指定内容、明确只做本轮局部且暂不追问并已完成局部交付，或任务结束时使用；状态必须相应为 `paused`、`scope_limited:true`、`local_only:true` 且 `local_done:true`，或 `complete`，并填写对应来源和 `semantic_review`。暂停、范围限定或局部处理恢复原任务时，旧豁免必须清除或重新取得来源。

`final` 要求讨论阶段最后一条非空正文是一个问题，并同时核对 `next` 的当前动作和 `semantic_review` 契约；活动插问、未完成覆盖检查、阻塞操作及其他尚未接回的事项不能借最终问题或免问类型绕过。问题之后出现选项、总结或其他内容时校验失败；正文没有问号、最后一行不是问题、或只在中途提问也不能通过。`draft_reply` 必须显式传入字符串，即使当前不需要提问也不能省略。

`semantic_review` 的 `reviewer` 为 `main` 或 `independent`，`target` 为 `decision`、`plan_transition` 或 `waived`，`status` 仅在语义检查通过时为 `pass`，并提供实际来源。`independent` 还必须填写实际 `review_id` 和 `authorization_source`；没有独立能力或授权时使用 `main` 并保留自检限制。检查项按交接类型填写：`decision` 使用 `target_is_current`、`not_already_decided`、`not_delegated`、`answerable_now`、`single_question`、`no_trailing_content`，计划请求仍有缺口时另加 `incomplete_plan_delivered`；`plan_transition` 使用 `transition_intent`、`no_blocking_pending_decisions`、`single_question`、`no_trailing_content`；`waived` 使用 `waiver_source_is_explicit`、`no_user_question`、`no_trailing_content`。脚本只核对这些字段、状态和交接动作，不能判断问题是否扣题、是否重复、是否可回答，也不能证明复核来源真实。

用户明确限定本轮只交付指定内容、覆盖检查已完成且没有待交付计划请求时，脚本返回 `scope_complete`；正文交付后停止，不追加问题或推进下一阶段。`scope_limited` 可以保留尚未影响本轮局部交付的待决项，但不能越过计划请求、计划/目标展示要求、未完成局部动作、覆盖检查、活动插问或阻塞操作。

插入请求使用 `interruptions` 数组，原阶段和状态留在原字段。处理前以原状态调用 `next`，临时事项填 `id`、`request`、用户消息 `source`、`status:continue` 和 `next_action`；等待脚本返回，将 `resume_point` 原样放回该项并保留后，再调用临时事项的工具，不得并行。它只包含原环节、状态、下一动作及等待依据，不复制完整计划和目标；原待答问题不能因插问被记成已答。嵌套插入按顺序追加，不能覆盖未完成事项。

临时事项受阻时填 `blocked` 和 `wait_reason`，脚本返回 `wait_interruption`；等待用户时另填已展示问题的 `wait_evidence`。用户明确取消则记 `cancelled` 与用户来源，用户要求继续且权限允许时记 `continue`；按实际意思判断，不匹配固定关键词。完成或取消须填实际结果或取消依据 `result_evidence`，连同已保存的 `resume_point` 再调用 `next`；脚本返回 `reconcile_interruption` 和恢复点。先核对结果、最新要求及原状态，在正文交付临时结果或说明取消，再接回原事项；新信息影响原决定时只更新受影响部分，不预记正文已交付。恢复点缺失时从可用对话或摘要补查，不猜测。

原任务明确暂停时，仅在用户另行要求临时事项且未暂停全部工作时，才设 `allow_while_paused:true` 及其用户消息 `allow_while_paused_source`；接回后仍保持暂停。临时事项被用户暂停后恢复须提供 `resume_source`。原状态存在结构或执行门槛错误时，`original_state_errors` 须在恢复原任务前处理，不妨碍独立且获准的临时请求。恢复不必传两份完整状态；已有 `previous` 时仍可用于原有的跨轮检查。脚本只返回结果，不自行写记录或授予权限。

如果有正在运行或结果未知的操作，可用 `operations` 保存其 `id`、实际 `reference`、`status`、`side_effect` 和 `blocks_next`。`blocks_next`、`blocks_completion` 按依赖判断，与是否有副作用无关；`side_effect` 用于判断结果未知时能否安全重试。同一操作不应换标识重复记录；不阻止下一步不自动等于可以宣告整项完成。`check_operation` 仅核实原操作，在查询权限内不受后续执行许可缺失阻挡；结构错误仍须处理，查明后继续或重试仍须有效授权。即使当前状态是等待用户或等待工具，`blocks_next:true` 的已失败操作也先返回 `handle_operation_failure`，不能被等待状态遮蔽。

脚本返回下一动作供主控执行：主任务执行受阻但计划和目标可在授权内展示时，只能填 `independent_action` 为明确只读动作并设 `independent_action_read_only:true`；若动作可能有业务副作用，必须已有有效 `execution_receipt`、完整 gates、执行范围和许可动作，否则不能返回 `continue_local`。脚本返回 `continue_local` 时保留原阻塞原因。若该字段遗漏，但计划已展示、目标未展示且本轮不限于局部，脚本仍要求核对当前范围及确认依据，允许时一起展示计划和目标，不自行认定已授权。临时事项受阻仍保持等待。仍有影响方案的待决项时调查或讨论；用户要求计划且讨论闭合时列出计划，未闭合时可给标明缺口的草案；其他没有计划请求的情况按主控请求结束讨论。讨论闭合并进入正式计划阶段时同轮展示计划与目标；用户明确限定本轮只能展示其中一项时按主控等待调整限定。旧草案的待核实状态不能挡住已确认的正式计划。计划展示不是确认或执行授权。执行中准备继续实际操作时，覆盖尚未核对或仍有影响方案的待决项，脚本要求先修正状态并处理缺口；已完成的本轮局部动作可按限定收口，但存在 `running/unknown` 且 `blocks_next:true` 的操作时先核实，操作失败时返回 `handle_operation_failure`，成功后才允许 `local_complete`。用户暂停或明确限制本轮范围时优先遵从；未知副作用先核实原操作，不盲目重试。

目标展示后进入执行、验证、审查或完成时，必须传入 `{"previous":上一状态,"state":当前状态}` 检查明确变化；没有上一状态时脚本返回 `repair_state`，不能新目标直接通过 `next`/`check`。其他场景涉及计划请求撤回、暂停恢复或决定变化时也应按需传入上一状态。输出 `scope: structure_and_changes`；`decided`、`delegated`、`excluded` 的变更和删除均核对来源及沿用授权的影响；同一事项在有效委托内调整实际决定，可复用原来源，并在现有 `impact_review.reason` 说明委托范围和影响，不另索授权。若本次计划已在上一状态交付而本轮才清除请求，记录 `plan_request_delivery_source` 指向本次实际交付；旧计划不能冒充新请求的交付。脚本输出的 `scope: structure_only` 表示只检查结构；它不验证来源的真实性、决定是否被正确理解、问题覆盖是否完整或消息是否实际送达，也不能强迫模型调用。不可访问消息记录文件不妨碍通过可用对话判断下一步；证据不可核实就保留未知，不把普通文件冒充宿主回执。原有摘要的写入、并发和恢复仍由[记录模块](state-recovery.md)处理，本检查器不替换摘要文件。
