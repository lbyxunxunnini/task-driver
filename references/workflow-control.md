# 轻量状态检查

主控必须在对话或[唯一任务摘要](state-recovery.md#何时建立记录)中维护原目标、当前环节、已决定事项及来源、未决事项、下一动作和授权。目标确认后，正常讨论必须在当前项目的唯一任务摘要中维护状态；用户明确只读时在上下文内维护。达到[记录条件](state-recovery.md#何时建立记录)时，必须按记录规则建立或复用同一任务摘要，增量维护问题和回答。禁止为状态检查重复询问已确定事项或制造新问题。

## 强制入口与失败关闭

`workflow_control.py` 为主控提供只读结构检查，流程动作由主控决定。主控每完成一个阶段结果，以及准备提问、展示计划或目标、启动子代理或开始执行前，必须调用 `next` 并执行返回动作。讨论最终回复和正式计划正文必须调用 `final`。准备业务执行时还必须调用 `begin`，并取得 `ok:true` 与 `execution_receipt` 后再启动第一项。

脚本读取标准输入或指定 JSON；讨论阶段的 `final` 还读取指定任务摘要。`next --state -` 从标准输入读取状态。`begin` 只返回一次性结构回执。讨论阶段的 `final` 从 `{"state":{...},"draft_reply":"最终回复草稿","discussion_handoff":{...},"discussion_record":{...}}` 读取状态、正文和唯一交接对象。`check` 只检查结构。

### 新任务开场 intake

主控收到新任务时先调用 `python3 /absolute/path/task-driver/scripts/workflow_control.py intake --state -`，从标准输入传入开场信息。此时还没有阶段状态。按返回动作组织当前一问并等待：首次复述整体理解；已经有部分明确答复时，仅核对仍影响交付的关系，不重复全部目标。`goal` 填核对后的完整理解，保留本轮补充涉及的原限定及其承接结果，不能先省略限定再登记确认。`confirmation_source` 只能在完整答复与上一问核对后填写，不能只摘一个肯定词而忽略同条补充；无法明确承接时仍停在理解核对，不将自行改写的目标当成已确认目标。

| 实际已知的信息 | 输入示例 | 主控下一动作 |
| --- | --- | --- |
| 尚未说明目标 | `{}` | 按 `ask_goal` 询问用户希望达成的结果 |
| 已说明目标，尚待确认理解 | `{"goal":"每周导出一份可打印的报告"}` | 按 `confirm_understanding` 复述首次理解，请用户确认。确认后的补充与修订按主控入口仅核对受影响部分 |
| 用户已确认这份理解 | `{"goal":"每周导出一份可打印的报告","confirmation_source":"用户第 3 条消息确认上述目标"}` | 按 `continue_analysis` 进入 `phase:analysis` 开展深度分析 |

复用对话中实际发生的确认。开场无需填写决定、覆盖核对、讨论闭合、计划或授权。恢复已有任务继续用原快照和原入口。

### 调用与纠错

构造检查器 JSON 时依据本文对应环节的字段说明和示例，先运行检查并读取返回结果，不预读检查器源码或遍历其他环节来推演全部校验条件。已有输入复用未变字段；返回错误时先按 `errors`、`diagnostics` 和对应字段说明修正。只有实际错误仍无法解释时，才定位相关源码片段，禁止为一次正常调用通读检查器。此规则只限制检查器源码预读，不代替讨论、记录等职责模块，也不减少原有调用时点、来源核对或语义复核。

`phase` 必须使用 `analysis`、`discussion`、`planning`、`goals`、`execution`、`verification`、`review` 中的值。计划阶段必须写 `planning`，禁止写 `plan`。脚本为已知错误附加 `diagnostics`，提供字段位置、可用证据或修正指引，目标快照有差异时列出可定位的目标编号。原 `errors`、路由、退出码及授权检查保持原语义，脚本无自动补值功能。必须按报错和真实现场修正输入，禁止补写未发生的展示、确认或执行证据。

必须使用可访问的 Skill 绝对路径调用脚本。相对状态文件路径按调用时的工作目录解析。已有获准保存的输入文件时，可直接调用，无需临时编写 Python 包装脚本。

```bash
python3 /absolute/path/task-driver/scripts/workflow_control.py next --state /absolute/path/current-state.json
python3 /absolute/path/task-driver/scripts/workflow_control.py final --state /absolute/path/final-input.json
```

示例路径必须替换为实际位置。`current-state.json` 可使用实际状态，或含 `state`、`previous` 的对象。`final-input.json` 必须使用完整的回复输入结构，需要跨轮检查时必须附上 `previous`。无需持久记录时优先用宿主支持的标准输入传递同一 JSON（`--state -`）。使用 `--json` 前必须确认输入较短且能够正确引用。禁止将长正文拼成多层 Shell 转义，或为调用强行新建记录文件。工具拒绝时必须说明实际限制，禁止换用其他写法绕过拒绝。任何调用方式都必须遵守 `next`、`final`、`begin` 原有执行时点和失败关闭要求。

### 复用已有状态

恢复时已有同一任务在本次变化前的最后一份有效完整状态，可以将其作为 `check`、`next`、`begin` 或 `final` 的 `previous`，只提交实际变化。可用 `--previous-state` 读取获准保存的完整状态文件，也可在输入中提供 `previous` 快照对象。增量输入必须使用 `changes`，禁止同时提交完整 `state`。下面的输入适用于 `wait_tool` 等待的唯一操作已成功返回的情况。

```bash
python3 /absolute/path/task-driver/scripts/workflow_control.py next \
  --previous-state /absolute/path/verified-state.json --state -
```

```json
{
  "changes": [
    {"path": ["operations", 0, "status"], "value": "succeeded"},
    {"path": ["operations", 0, "evidence"], "value": "实际操作回执的位置"},
    {"path": ["status"], "value": "continue"},
    {"path": ["next_action"], "value": "核对原操作返回的结果"},
    {"path": ["wait_reason"], "remove": true}
  ]
}
```

`path` 必须从顶层开始，使用字段名和从 0 开始的列表下标。必须先核对下标对应的实际步骤或操作 ID。设置或替换指定位置的值必须用 `value`，删除已存在的对象字段必须用 `remove:true`，增删列表条目必须替换整个列表。变化按顺序应用，中间路径必须已存在。`final` 必须在输入外层提供 `draft_reply`。讨论阶段还必须在同一层提供 `discussion_handoff`。

脚本先验证旧快照结构，再用合成后的完整状态执行原有跨轮、执行回执和回复检查。必须复用仍有效的来源和观察，据实更新受影响的来源、旧等待依据或失效回执，显式移除需要清除的字段。需要读取合成结果时可加 `--emit-state`，调用方必须按原规则处理成功输出的 `state`。`begin` 返回的 `state` 是实际检查过的执行前状态，新回执另行返回，必须按[回执记录规则](#首次执行的确认顺序)保存。脚本只读。缺少有效快照时必须传入完整状态，禁止为使用增量模式重造“已验证”快照。

### 首次从讨论转入计划

讨论收口必须遵守[主控入口](../SKILL.md#接到任务后的第一步)。状态检查记录该流程实际发生的事件，并按以下规则填写输入和处理返回结果。

1. 覆盖尚未核对或仍有影响方案的待决项时，必须先补查可核实事项，再就仍需用户决定的事项使用 `decision` 交接。收到用户答复后必须重新核对剩余待决项。仍有待决项时禁止请求结束讨论。用户明确要求草案且正文仍有缺口时，可按当前计划请求交付标明缺口的讨论稿，并遵守[讨论最终回复](#讨论最终回复)的交接要求。
2. 覆盖核对通过且没有必要待决项时，`next` 返回 `request_plan_transition`。 首次发送这道问题前，当前状态保持 `continue`，`next_action` 记录待发送的收口问题；不得预填该问题的 `wait_evidence` 或 `discussion_closure_question_source`。`final` 成功后直接发送已核对的正文，不在发送前追加一次“已送达”的状态写入。必须用 `plan_transition` 实际询问用户是否结束讨论并开始展示正式计划和验收目标，发出后必须停在讨论阶段等待答复（`phase:discussion`、`status:wait_user`）。`wait_evidence` 和 `discussion_closure_question_source` 必须引用同一个实际发出的问题。等待期间必须沿原状态续接，插问答完可回到同一个收口问题。开场要求计划、要求直接实施、回答单项或补充材料时，必须仅更新对应意图或讨论内容，禁止登记为收口答复。
3. 必须取得用户针对这道收口问题的明确肯定答复，并核对范围与决定仍然有效，再记 `discussion_closed:true`。`discussion_closure_question_source` 必须指向实际发出的问题，`discussion_closure_source` 必须指向用户对该问题的肯定答复，两者必须来自不同消息。用户继续讨论或新信息使原问题失效时，必须继续处理受影响事项，并按当前范围重新收口。主控必须对照对话核对问题是否实际发出、答复是否同意当前范围，脚本只核对结构。
4. 调用 `next` 时必须同时传入问题发出后的实际待答状态 `previous` 和收到答复后的实际 `state`，两者可从上下文恢复。检查器核对待答问题的引用及前后影响方案的决定。首次展示必须有有效的收口问答。取得 `present_plan` 后必须进入 `planning`，并在同轮展示正式计划和验收目标。禁止在收口确认前展示正式计划或验收目标或开始执行。展示后仍必须另行取得针对已展示内容的[执行确认](#首次执行的确认顺序)。旧计划需要补齐目标时，`previous` 必须保留实际展示过的旧计划及来源。明确暂停、仅交付其他局部内容、任务到此结束或已有结果满足任务时，必须按[相应交接](#讨论最终回复)处理。

首次展示正式计划前，即使草稿已写好，`plan.presented` 也必须保持 `false`，目标也必须保持未展示。必须使用真实状态调用 `next`，取得 `present_plan` 并按[正式计划正文检查](#正式计划正文检查)校验后再发送正文。禁止将即将发送的“本轮最终正文”填为已发生的 `evidence` 或 `wait_evidence`。下例是用户已明确肯定收口且正式计划仍未发出时的 `state`。必须用实际决定和消息来源替换示例，禁止把空决定列表当作自动闭合。

```json
{"task_id":"当前任务","phase":"discussion","status":"continue","next_action":"核对收口答复后展示正式计划和验收目标","decisions":[],"plan":{"presented":false},"coverage_checked":true,"plan_requested":false,"discussion_closed":true,"discussion_closure_question_source":"实际发出的收口问题消息","discussion_closure_source":"用户肯定答复的消息","gates":{"plan":null,"goals":null,"execution":null,"subagents":null}}
```

必须在正文实际发出后，才按可核实的送达事件或下一轮对话记录更新展示来源。宿主发送正文后无法再调用工具时，必须保留待同步，并在下一次自然续接时补齐，禁止额外索取用户回复。修订旧计划时必须保留真实历史和版本对应，禁止清空 `presented` 或删除来源来绕过变更核对，禁止把尚未发出的新增内容写成已展示。

脚本未运行、执行失败、输入不完整或结果无法解析时，必须停在当前阶段，按[主控失败处理](../SKILL.md#不可短路主控)记录状态并停止执行、子代理和交付动作。禁止自行把字段填为已通过。主模型可在明确说明限制后按主控规则人工核对讨论和只读调查，禁止以人工核对继续上述已停止的动作。

### 状态字段

状态必须包含 `task_id`、`phase`、`status`、`next_action`、`decisions`、`plan`、`coverage_checked`、`plan_requested` 和 `gates`，执行前必须另有 `goals`。决定项必须记录稳定 `id`、主题 `subject` 和 `status`。`decided` 和 `delegated` 必须有实际决定 `value` 及 `source`。已获委托而模型尚未作出决定时，必须保持 `pending` 并保留委托来源，由模型落实。`pending` 可省略 `value`。用户只回答一部分时，必须仅更新实际覆盖的决定。填写前必须核对对话和材料，无法恢复的事实必须保留未知，禁止猜测。

计划与目标的 `presented` 和 `evidence` 必须来自对话中实际可见的内容。首次同轮正式展示时，计划与目标必须共享同一个 `presentation_id`。局部调整必须分别保留原展示和增量展示的可追溯引用，禁止把未展示过完整原文的增量当作首次完整展示。展示前可以省略 `goals`。进入执行时必须填写 `goals`，如 `{"presented":true,"evidence":"实际目标展示来源","presentation_id":"计划展示消息"}`。除下述免计划收口外，`goals.presented:true` 必须对应 `plan.presented:true`。禁止仅展示目标或拆轮首次展示两者。除该例外外，`plan.presented:false` 而目标已展示属于结构错误，必须回到计划展示处理。

`plan_required:false` 必须仅用于无需进入正式计划阶段的收口，如已有结果满足任务。该例外缺少计划展示时，`plan_waiver_source` 必须记录“已有结果满足任务”的实际来源。禁止用免计划字段跳过应当展示的计划。`plan_requested` 必须记录当前待处理的明确计划请求，用于跟踪草案及交付。计划请求与授权必须分别保留来源。收到「讨论完给我计划」时，必须记为后续交付要求，当前仍按[收口规则](#首次从讨论转入计划)推进。

`plan_request_source` 必须使用能唯一标识该次请求的实际消息引用。同一请求的草案已实际交付时，`plan.draft_for_request` 必须填写完全相同的请求引用。有依据确认旧草案不对应当前请求时，`plan.draft_not_for_request` 必须填写当前请求引用，禁止编造无法恢复的旧请求来源。新草案实际交付后，必须更新草案证据和 `draft_for_request`，并清除对应的 `draft_not_for_request`。禁止预记交付。引用差异可能来自书写方式，未确认关系时脚本返回 `verify_plan_request`。必须先核对对话再更新，禁止推定已送达或重复提问。确实无法判断时必须保留未知，禁止假称已核实。

编号计划必须写入 `plan.steps`。每项必须有稳定 `id`、`action` 和 `status`，状态必须使用 `pending`、`in_progress`、`done`、`blocked` 中的值。`done` 必须有实际证据，`blocked` 必须说明原因。必须按列表顺序推进，禁止以重排改变推进顺序。一个计划最多允许一个进行中步骤，前项未完成时禁止将后项标为 `done`、`in_progress` 或 `blocked`。默认收口时全部步骤必须为 `done`。

全部步骤为 `done` 时，`next` 返回 `steps_complete`。主控必须进入验证与审查，禁止继续用 `next_action` 做未列入计划的新业务动作。

业务执行入口还必须有 `analysis_complete`、`analysis_evidence`、`discussion_closed`、`discussion_closure_source`、`execution_scope`、`execution_begun` 和 `execution_receipt`。新建或更新的 `execution_scope` 必须记录 `allowed_paths`、`allowed_actions`、授权来源及 `subagent_policy`。后者包括执行分派（`execution: as_needed | disabled`）与独立复核（`review: enabled | disabled`）；另有明确的代理用途限制时写入 `restriction`，并以权限范围及原来源共同约束分派。App、H5 的 `execution` 必须为 `disabled`。这两个决定随 `execution_scope` 一起进入执行回执。仅调整独立复核时，更新 `gates.subagents` 并重新检查执行入口，保留原业务执行范围、确认来源和已完成步骤。执行分派的实际权限变化时，按执行范围的新授权处理。`allowed_actions` 必须精确覆盖所有 `plan.steps.action`。`execution_receipt` 必须等于当前结构授权哈希。目标、计划、执行授权、执行范围、独立复核设置或目标跟踪方式变化时，旧回执失效，必须用对应的实际 `previous` 重新运行 `begin`。

计划步骤新增、删除、重排或动作变化时，必须记录 `plan_revision_source`。开始执行后改变执行范围或目标跟踪方式时，还必须记录 `execution_reset_source` 并将 `execution_begun` 恢复为 `false`，随后重新运行 `begin`。

### 首次执行的确认顺序

首次 `begin` 的 `previous` 必须使用用户同意执行前的实际展示状态（`planning` 或 `goals`），其中计划和目标必须已实际送达。必须通过现有对话状态保留或从可见消息恢复该快照，直至获得执行回执。当前状态的计划步骤、目标范围和展示来源必须对应同一版本。`gates.execution` 必须引用展示后用户明确同意启动的实际消息。禁止把开场请求、讨论收口答复或助手展示消息登记为执行确认，禁止用同一个当前状态填写 `previous` 和 `state`。无法核实历史时，必须按当前阶段补齐实际展示或执行确认。本轮仍限定只看方案或只读时，禁止签发执行回执。

更改执行范围时，即使原编号步骤不变，也必须先在修订计划中展示范围变更，再取得针对新范围的执行确认。仅更换目标跟踪载体，且计划、目标和执行范围均未变化时，续接可以复用更换前已取得的有效执行确认。

记录执行回执时，必须用 `begin` 实际核对过的当前状态作为下次状态检查的 `previous`，再更新 `execution_begun` 和 `execution_receipt`。可用 `begin --emit-state` 取得该快照。授权内容变化时必须重新走入口，禁止直接替换回执。

首次 `begin` 禁止提交已完成或进行中的步骤。重新 `begin` 时，必须使用变更前最后一份有效执行快照作为 `previous`，保留原回执供核验，并在当前状态填写新的有效授权与重置来源。禁止沿用旧回执执行。继承进度前，必须核实原执行有效且属于同一任务，并核对编号、动作、状态和证据都与原快照一致。还必须反向核对原已完成步骤，编号和动作未变时禁止退回待办，即使计划展示来源已更新。原操作仍在运行或结果未知时，必须先核实原操作并保留同一操作的结果回执。必须取得新执行回执后从剩余或进行中步骤继续，禁止清零已完成部分。

执行阶段使用 `local_only:true` 时，必须另填 `local_only_source`，保留用户明确限定本轮局部任务的实际来源。禁止借无来源的局部限定绕过步骤和完成门槛。

分析阶段只返回 `continue_analysis`。禁止把 `next_action` 写成业务写入。执行前使用 `local_only` 时必须另有 `local_only_source` 和 `local_only_read_only:true`。

必须用 `goal_tracking_mode`、`goal_tracking_source` 和 `goal_tracking_confirmation_source` 记录目标跟踪方式。`host` 模式必须有真实 `goal_tracking_host_id` 和 `goal_tracking_host_receipt`。`plan` 或 `conversation` 模式必须有稳定的 `goals.local_goal_id`、`goal_tracking_fallback_reason`、`goal_tracking_fallback_evidence` 和用户确认来源。跟踪方式为 `unavailable` 时禁止进入执行。展示并确认验收目标与创建宿主 Goal 分别取证。

`host` 模式必须按真实工具类型设置 `goal_tracking_host_kind` 为 `aggregate` 或 `task_list`，禁止从返回条数推断。必须另存 `goal_tracking_host_readback`，格式如 `[{"host_id":"实际 ID","objective":"G1：已确认的通过条件"}]`。读回必须取自实际创建返回或查询结果。任务列表的 `host_id` 必须各不相同，原 `goal_tracking_host_id` 必须对应其中一个。脚本校验正文与 `included` 一一对应，来源真实性由主控核对。旧状态缺少读回字段时必须从真实回执补录，禁止自行补写或因补录重建目标。

有替代记录的旧宿主目标无法同步时，已执行后的只读验证、审查（`read_only:true`）及业务收尾可按新范围继续，禁止启动新的业务执行。范围变化致旧 `execution_receipt` 与当前范围不符时，必须保留原 `begin` 状态的授权载荷（按脚本 `execution_authorization_payload` 取值），记为 `prior_execution_authorization`。只读收尾必须核对原任务和原回执哈希，禁止用旧授权开始或恢复写入或派发子代理。列表的替代例外必须仅用于有替代记录且旧正文匹配的宿主任务。该旧条目必须用 `replacement_goal_ids` 指向取代它的当前验收项，纯删除时必须用空列表。其余任务仍必须逐项匹配。

等待用户或工具期间，主控必须只采纳标记为 `independent_action_read_only:true` 且精确列入 `read_only_scope.allowed_actions` 的独立动作。禁止执行检查器返回的其他独立动作。非等待状态下，可能产生业务副作用的独立动作必须先满足完整执行入口和有效回执，并精确列入 `execution_scope.allowed_actions`。

验证或审查阶段若 `execution_occurred:false`，必须显式设置 `read_only:true`。缺少该标记时必须按执行入口未完成处理，禁止借已有结果直接写报告或业务产物。

### 本轮限定与目标状态

`discussion_question_waiver_source` 必须记录实际消息来源，仅用于用户明确暂停、明确只做本轮局部且已完成交付，或任务结束。`scope_limited:true` 时，`scope_limited_source` 必须记录本轮限定的原话及范围。禁止用工具等待或外部阻塞填报这些豁免。

`goals` 必须仅保留当前有效目标。目标变化时，`superseded_goals` 必须保存旧目标原文、`host_id`、新范围来源及 `superseded_by`，禁止把已取代的目标标作当前目标。`host_goal_sync` 必须据实际同步情况记录 `synced`、`stale` 或 `unavailable`，并满足下述宿主 ID 约束。完成时可同时报告业务已验收和宿主目标 `stale/unavailable`。

无 Goal 模式时，`superseded_goals` 的 `host_id` 可为空或 `null`，但必须提供稳定的 `local_goal_id`。当前 `goals` 也必须记录同名的稳定 `local_goal_id`。有真实宿主目标时，必须优先保留 `host_id`。禁止伪造宿主 ID。

`host_goal_sync` 为 `synced` 或 `stale` 时，必须仍有非空宿主 `host_id`。纯本地目标或无 Goal 模式时必须使用 `None` 或 `unavailable`，禁止声称宿主目标已同步。

目标展示时，`goals.included` 必须仅包含 `kind:changed`（改动直接结果）或 `kind:associated`（直接关联结果），每项必须有 `id`、`criterion` 和 `source`。`goals.excluded` 每项必须有 `id`、`item` 和用户 `source`。`goals.evidence_map` 必须按当前 `included` 的 `id` 保存[证据记录](verification.md#执行验证)列表。例如 `{"G1":[{"kind":"tool","source":"本次测试原始输出或可回查工具事件","subject":"实际被测构建或版本","observed":"明确输入下的实际断言结果"}]}`。旧字符串引用可用作查证线索，必须从实际来源核对并补录，禁止只换格式。默认完成时，每个 `included` 必须有结构化证据。按用户要求结束且缺少该记录时，相关目标必须列入未验证。禁止在 `evidence_map` 中使用 `excluded` 或未知 ID。证据来源、测试覆盖及版本的真实性和适用性必须由验证和审查核对。

`goal_scope_baseline` 必须保存最后一次已确认目标的 `included` 与 `excluded` 快照。初次展示时，必须建立与当前目标一致的基线。目标临时为 `presented:false` 时必须保留旧快照。用户变更范围、取得实际来源并记录 `superseded_goals` 后，必须把基线更新为新范围。跨轮核对必须遵守[跨轮状态核对](#跨轮状态核对)。

完成时默认必须使用 `completion_basis:evidence`。用户明确要求结束且仍有未验证 `included` 时，必须使用 `completion_basis:user_requested`，填写 `completion_request_source` 和 `completion_report`（`verified_goal_ids`、`unverified_goal_ids`），在 `unverified_goals` 中逐项记录 `id`、`item`、`reason` 和 `impact`。若仍有未完成步骤，还必须在 `unverified_plan_steps` 中逐项记录 `id`、`action`、`reason` 和 `impact`，并如实报告“业务已按用户要求收口”及仍未验证的内容。用户要求变更目标时，必须先更新 `included` 和 `excluded`，记录新目标的实际来源，并保留 `superseded_goals`，禁止直接沿用旧目标完成。旧目标缺少新字段时，脚本返回 `repair_state`，必须先[迁移目标结构](state-recovery.md#引用与展开)，禁止省略 `goals` 后完成。

以下是结构示意，必须按实际对话填写。禁止把示例当作已有决定。

必须在 `gates.execution` 记录执行范围依据，在既有 `gates.subagents` 记录用户选择开启、不启用、限定用途或明确委托模型决定独立复核的实际消息来源。旧状态必须核对原话及当时选项的实际范围。旧选项「不开启子代理」按执行分派与独立复核均关闭承接；「仅允许执行代理」保留原工作边界并关闭独立复核；「仅审查」关闭执行分派并按原范围复核。旧版普通开启按当时实际说明承接，再应用当前任务类型的限制。旧回执缺 `subagent_policy` 且原权限未变时可续用，必须先按原话还原限制，禁止套用新默认而扩权。需要改变实际权限时，按本节保留原证据并重新取得有效回执。缺字段时，必须先从可用对话或记录补查，禁止从执行授权推定独立复核设置。仍无法确认时必须保持缺失，执行前必须按主控询问。对运行中或结果未知的原操作进行只读核实时，可在缺少这两项依据的情况下继续。来源内容是否支持设置必须由主控核对。

```json
{"task_id":"当前任务","phase":"analysis","status":"continue","next_action":"分析当前请求","decisions":[],"plan":{"presented":false},"coverage_checked":false,"plan_requested":false,"gates":{"plan":null,"goals":null,"execution":null,"subagents":null}}
```

## 正式计划正文检查

必须按[计划覆盖核对](planning.md#正式计划的覆盖核对)整理本次展示所依据的必要行为，用 `final` 检查实际待发送的正文。首次展示正式计划时，必须使用 `planning` 阶段、尚未展示的当前状态和可核实的 `previous`。已展示后补齐或修订时，必须在 `planning` 或 `goals` 阶段沿用原展示记录及现有权限。正式修订必须在 `final` 输入中标明 `formal_plan:true`。首次展示、旧计划补齐和正式修订都必须提交 `plan_coverage`，普通内容确认无需提供。执行受阻且本轮专门补齐旧计划和目标时，必须按 `next` 返回的 `plan_supplement` 处理。一般独立查询必须沿用原分流。暂停、有阻塞待决项或仍依赖原操作时，必须先处理当前下一动作。禁止在正文送达前标记为已展示。

必须在现有 `state`、`previous` 和 `draft_reply` 外加入 `plan_coverage`。每项必须提供可核对的实际来源和短而明确的触发、结果片段。例如 `[{"source":"用户确认的歌词编辑交互","trigger":"沿歌词连续滑动","expected":"选区随手势更新"}]`。触发与结果必须放在同一条验收描述或同一段，有缺项时必须先补齐正文。脚本将空白归一后核对该对片段是否同时出现，检查范围是传入清单和正文的对应关系。有依据的额外来源及范围取舍仍必须由主控核查。此检查必须沿用现有回复时点，无需保存新状态或再次询问已确认事项。

## 讨论最终回复

正常讨论必须以一个当前内容问题或转阶段问题收口。免问和等待必须使用下列对应交接类型。

讨论阶段最终回复示例（`semantic_review` 只表示语义复核契约已填写，不证明复核者真的独立或判断正确）：

```json
{"state":{"task_id":"当前任务","phase":"discussion","status":"continue","next_action":"询问当前必要事项","decisions":[{"id":"D1","subject":"当前取舍","status":"pending","question":"当前取舍上你希望采用方案 A，还是方案 B？"}],"plan":{"presented":false},"coverage_checked":true,"plan_requested":false,"gates":{"plan":null,"goals":null,"execution":null,"subagents":null}},"discussion_record":{"project":"/work/report","summary":".task-driver/周报-计划摘要.md","turn_id":"用户第 3 条","answer":"先导出 PDF。"},"draft_reply":"分析结果如下。\n\n当前取舍上你希望采用方案 A，还是方案 B？","discussion_handoff":{"kind":"decision","decision_id":"D1","semantic_review":{"reviewer":"main","status":"pass","target":"decision","decision_id":"D1","source":"主控按当前对话复核","checks":{"target_is_current":true,"not_already_decided":true,"not_delegated":true,"answerable_now":true,"single_question":true,"no_trailing_content":true}}}}
```

`discussion_handoff.kind` 必须使用下列值之一。

- `decision` 用于存在阻塞计划的 `pending` 决定时。该决定必须填写 `question`，`decision_id` 必须对应其中一项。必须通过 `semantic_review` 核对正文问题实际对应当前待决项，无需逐字复制 `question`。待决项缺少显式问题、语义复核目标不一致或复核未通过时，校验失败。`next` 返回 `present_incomplete_plan`，或计划请求仍有缺口时，正文还必须交付绑定当前 `plan_request_source` 的缺口草案，语义复核必须填写 `incomplete_plan_delivered:true`。只问问题时计划请求仍待交付。
- 新任务首次收口前，逐项对照原始请求、用户答复和已有记录。在每条 `decided`、已落实的 `delegated` 和 `excluded` 决定上填写 `implementation`（实际怎么做）和 `verification`（用什么观察判定是否满足）。排除项说明如何守住边界及如何核对。保留原 `id`、`value` 和 `source`，排除项无原值时显示主题。两种复核方式都须在正文为每项单列一句，格式为“原值：做法，核验时验法。”，可加列表符。例如记录 `{"id":"format","subject":"报告格式","status":"decided","value":"交付 PDF","source":"用户第 2 条：交付 PDF","implementation":"导出定稿","verification":"打开文件比对页数","detail_source":"已确认的交付说明第 3 段：导出定稿，打开文件比对页数"}` 对应正文“交付 PDF：导出定稿，核验时打开文件比对页数。”。
- 主控自检时，做法和验法须能在本项的原值、原来源或补充依据 `detail_source` 找到对应片段。补充依据引用真实方案、规则或调研记录的位置和原文。主控核对它是否支持该项，发现新取舍时回到讨论。收口正文必须逐项展示上述各句，可补充整体思路、必要解释和限制，最后另起一行写“是否结束讨论并开始展示正式计划和验收目标？”。补充内容须纳入同一次语义复核，不得新增未经决定或委托的实质取舍。存在补充正文时，`semantic_review.reviewed_reply_sha256` 填完整 `draft_reply` 的 UTF-8 SHA-256，`checks.no_new_material_choices:true` 记录复核结论；正文改变后重新复核并计算哈希。字段层级为 `{"semantic_review":{"checks":{"no_new_material_choices":true},"reviewed_reply_sha256":"实际哈希"}}`；合并到原复核对象，不能覆盖其他必需检查项。可用 `hashlib.sha256(draft_reply.encode("utf-8")).hexdigest()` 计算。哈希仅绑定已复核的草稿，不证明语义正确；发现新取舍时不能填写通过。`discussion_handoff.approach_basis` 是单个对象（不是数组），以 `decision_id` 指向实际采用做法的一条记录，`source_quote` 逐字摘自该记录的 `source`；该字段只存短摘录时，引用短摘录，不改用整条消息。已定做法的原值须出现在引文中。简答确认须引用提案及答复，委托须引用授权对象和范围。只要求比较资料不能作为采用某方案的依据。
- 主控自检与获授权的独立只读复核均允许逐项说明以外的正文自然措辞。复核者须先读原始请求、答复、调研和完整待发正文，再比对决定及依据，漏项或新增未经决定或委托的实质选择须退回；不得仅为补充正常说明而派发独立代理。等待已发出的同一收口问题时沿用原记录；旧执行恢复无需补写首次收口字段。
- 首次提出收口时，`discussion_handoff.choice_basis` 必须覆盖原请求和待发方案中的实质选择。已决定、已落实委托及已排除的记录都须引用，每项以 `decision_id` 和以原值填写的 `choice` 对回记录。决定来源必须支持采用该做法，范围或调研指令只支持其自身。排除项缺少原值时引用其主题，来源只支持排除本项。没有已决记录且确无实质选择时，用只含 `no_material_choice_reason` 的对象说明理由，并按下文提供已确认要求和限制做法的证据。空记录和单独一句理由无法通过新任务首次收口。检查器只验证引用及结构，语义由主控核对。恢复等待同一收口答复时复用原核对。
- `plan_transition` 用于已核对覆盖、没有阻塞计划的待决项，且本轮计划尚未展示时。`next` 必须已返回 `request_plan_transition`。重开讨论时必须保留旧展示来源。最后一个问题必须符合[收口要求](#首次从讨论转入计划)，语义复核必须核对过渡意图。两种复核方式均保留上文的可校验摘要，并按同一规则核对补充说明。
- `waived` 仅用于用户明确暂停、明确限定本轮只交付指定内容、明确只做本轮局部且暂不追问并已完成局部交付，或任务结束。状态必须相应为 `paused`、`scope_limited:true`、`local_only:true` 且 `local_done:true`，或 `complete`，并填写对应来源和 `semantic_review`。用户明确只要有缺口的讨论稿时，`scope_limited_source` 和 `plan_request_source` 必须引用同一消息。必须按草案动作写正文并使用 `waived`，语义复核必须用 `draft_only_scope:true` 确认用户限定，用 `incomplete_plan_delivered:true` 核对待发正文包含草案。正式计划的限定交付必须在收口问答期间保持有效，交付完成并恢复原任务时必须清除旧限定。暂停或局部处理后恢复原任务时，必须清除旧豁免或重新取得来源。
- `tool_wait` 仅用于当前状态及 `next` 路由均为 `wait_tool`，且没有阻塞讨论的待决事项、待交付计划草案、活动插问或可继续独立工作的情况。用户明确限定只交付查询完成后的正式计划和目标时，范围和请求必须引用同一实际消息，语义复核必须确认 `formal_plan_only_wait:true`。必须已完成覆盖检查，正文必须说明实际等待原因与续接点，禁止提问。可报告尚在运行或结果未知的原操作。阻塞操作明确失败时必须先分类。必须保留原阶段、授权及操作标识，结果返回后必须重新核对状态并续接。禁止把等待记为用户暂停或目标完成。

### 已确认要求只有一种做法

用户已经确认要什么，适用约束又唯一限定了怎么做时，把这一行放在 `state.confirmed_requirements`。每项沿用同一任务记录的稳定编号：`source` 摘录用户确认的要求（含 `value`），`constraint_source` 摘录用户指定或现行规则限定的唯一做法（含 `implementation`）。`verification` 须能对回本项的依据，可用 `detail_source` 补充。主控须核查原文确实只允许该做法。“参考文档提到某方案”本身不能证明唯一性。例如：

```json
{"id":"R1","value":"交付周报","source":"用户第 2 条：交付周报","implementation":"导出 PDF","constraint_source":"归档规范第 4 条：只能导出 PDF","verification":"打开文件核对页数","detail_source":"归档检查第 2 项：打开文件核对页数"}
```

当全部要求都走这条路径时，保持 `decisions:[]`，照常逐项说明并问收口，无需虚构 `approach_basis`。两种复核方式均检查正文；空决定不能用来附加建议。有实质取舍的行仍按决定记录和 `choice_basis` 核对，主控自检沿用已选做法的溯源要求。收口问答之间改变已确认要求需重新收口。

### 讨论摘要读回与正文展示

每次发出正常讨论回复前，更新摘要前必须读取或复用[记录模块的图表更新方法](state-recovery.md#同一份任务文档中的图与表)，按该方法增量更新同项目唯一任务摘要；本文只规定检查输入，不能代替编号和局部编辑规则。 表格已引用当前决定编号时，`final` 会检查图中是否仍有对应节点，缺失须恢复原节点，不能删除表格引用来绕过。随后将实际路径和本轮匹配字段交给 `final` 读回检查；无状态变化时只更新本轮标识和必要续接信息，不重写图表。在 `discussion_record.readback_ranges` 中指定需要核对的行范围，如 `[[12,18],[30,32]]`（从 1 起、含首尾），`final` 从同一次读取返回 `discussion_readback` 的实际磁盘片段与行号。首建或迁移核对图表；普通修改核对变更项及受影响内容；无状态变化时只核对本轮标识。主控审阅这些片段及上下文后再发正文，无需另做一次同内容读回；缺少实际片段或等价的保存后核对证据时，不能把 `ok:true` 当作语义核对完成。仅在失败或需要定位问题时使用下列命令单独诊断。相对摘要路径以项目目录为基准，绝对路径也须解析到项目内。摘要中维护一个 fenced Mermaid `flowchart TD`、一个标有“当前位置”的节点和一份有数据行的四列表（你确认的要求、当前做法或待决问题、怎么验、状态）。

```bash
python3 scripts/workflow_control.py record-check --project "$project" --summary "$summary" --turn-id "$turn_id" --answer "$answer"
```

从实际会话取得本轮消息定位，`discussion_record.answer` 和摘要“本轮答复”填写该条用户消息的原文摘录，首次方案讨论取本轮目标确认。此处的“答复”指用户的答复，不是助手待发正文或对用户意图的概括；只可省略无关片段、将换行折为空格，必须保留否定、条件、对象与范围。助手的解释和决定摘要留在对应记录，不放进原话字段。没有宿主消息 ID 时使用同一会话中的用户消息序号。摘要正文就地替换以下两行，历史答复留在决定记录。禁止从旧文件反推本轮期望值。

```text
本轮消息：用户第 3 条
本轮答复：先导出 PDF。
```

在 `final` 的输入顶层（与 `state` 或 `changes` 同级）传入以下对象。每次调用直接读回磁盘，匹配当前两行；文件缺失、跨项目、结构无效或本轮不符时返回 `ok:false`。旧快照可继续恢复，首次新讨论回复必须补录实际摘要。若用户明确限制只读，改传 `"discussion_record":{"read_only_source":"用户只读指令原文"}`，主控在上下文内维护记录。写入失败不能使用只读例外。

```json
{"discussion_record":{"project":"/work/report","summary":".task-driver/周报-计划摘要.md","turn_id":"用户第 3 条","answer":"先导出 PDF。"}}
```

讨论正文默认只展示业务内容，逐项收口保留每条要求、做法和验法，最后单独询问是否结束讨论。用户明确要看图或表时，`discussion_handoff.overview_request_source` 摘录该请求，只展示对应部分。主控负责核实来源和语义，旧图表送达记录不参与判定。

`final` 校验问题交接时，讨论阶段最后一条非空正文必须是一个问题。脚本同时核对 `next` 的当前动作和 `semantic_review`。禁止借最终问题或免问类型绕过活动插问、未完成覆盖检查、阻塞操作或其他尚未接回的事项。报告原操作仍在等待时，必须满足 `tool_wait` 的全部条件。问题之后出现选项、总结或其他内容时，校验失败。正文没有问号、最后一行不是问题或只在中途提问，也会失败。即使当前无需提问，也必须显式传入字符串 `draft_reply`。

`semantic_review` 必须填写 `reviewer`（`main` 或 `independent`）、与交接类型一致的 `target` 和实际 `source`。把 `status` 标为 `pass` 前，语义检查必须已实际通过。`independent` 还必须填写实际 `review_id` 和 `authorization_source`。独立复核不可用或未获授权时，必须由主控自检，填写 `main` 并保留自检限制。

检查项必须与交接类型对应。`decision` 必须填写 `target_is_current`、`not_already_decided`、`not_delegated`、`answerable_now`、`single_question`、`no_trailing_content`，计划请求仍有缺口时必须另填 `incomplete_plan_delivered`。`plan_transition` 必须填写 `transition_intent`、`no_blocking_pending_decisions`、`single_question`、`no_trailing_content`。`waived` 必须填写 `waiver_source_is_explicit`、`no_user_question`、`no_trailing_content`。`tool_wait` 必须填写 `tool_wait_is_current`、`no_blocking_pending_decisions`、`no_user_question`，来源必须引用实际工具观察，禁止引用用户暂停。脚本只核对字段、状态和交接动作。问题是否扣题、是否重复、是否可回答，以及复核来源是否真实，必须由主控核对。

用户明确限定本轮只交付指定内容、覆盖检查已完成且无待交付计划请求时，脚本返回 `scope_complete`。正文实际交付后必须停止本轮并保留整体任务恢复点，禁止追加问题或推进下一阶段。`scope_limited` 可保留尚不影响本轮局部交付的待决项。禁止以本轮限定绕过计划请求、计划和目标展示要求、未完成局部动作、覆盖检查、活动插问或阻塞操作。

插入请求必须用 `interruptions` 数组记录，原阶段和状态必须保留在原字段。必须先以原状态调用 `next`。临时事项必须填写 `id`、`request`、用户消息 `source`、`status:continue` 和 `next_action`。必须等待脚本返回，将 `resume_point` 原样放回该项并保存后，再调用临时事项的工具，禁止并行。恢复点只包含原环节、状态、下一动作及等待依据，禁止复制完整计划和目标。禁止仅因插问把原待答问题记为已答。嵌套插入必须按顺序追加，禁止覆盖未完成事项。

临时事项受阻时必须填写 `blocked` 和 `wait_reason`，脚本返回 `wait_interruption`。等待用户时必须另填已实际展示问题的 `wait_evidence`。用户明确取消时必须记 `cancelled` 与实际用户来源。用户要求继续且权限允许时，必须记 `continue`。必须按实际意思判断，禁止按固定关键词匹配。完成或取消时，必须填实际结果或取消依据 `result_evidence`，连同已保存的 `resume_point` 再调用 `next`。直接推进当前问题的信息更新主干，需单独处理的插问才在 `branch` 记录来源节点 `origin` 和 `relation`。有关联时用 `related`，补充受影响节点 `target` 和实际影响 `impact`；完全无关时用 `unrelated`。新证据要求修正 `relation`、`target` 或 `impact` 时，在该临时事项顶层的 `branch_revision_source` 填新事实及修正依据，须区别于上次依据，并保留原编号、`origin` 和 `resume_point`。改成相关分支时移除失效的返回字段；改成无关分支时移除 `target` 和 `impact`，按新归属核对返回条件，不能继承旧同意。归档时保留修正依据。

无关事项完成或取消后，有明确且仍有效的用户主动返回指令时，在临时事项顶层填写 `return_instruction_source` 的实际来源，不要求先发返回问题；处理中也可记录用户“完成后继续”的明确指令，但必须等该事项完成或取消才能返回。没有有效指令时按 `ask_return_to_main` 交付结果并询问是否回到原待答点，发出后填写 `return_question_source`；实际答复后填写 `return_answer:yes/no` 与 `return_answer_source`。主动指令与这三个问答字段互斥。后续拒绝、暂停或范围限制使旧指令失效时移除旧指令并保留新的限制来源；从拒绝转为主动返回时，使用新的用户来源并移除失效的问答字段。不得用旧指令覆盖新限制，也不得用对临时事项的继续要求解除主任务暂停。恢复时脚本返回 `reconcile_interruption` 和恢复点，移除该项时同步把分支记录追加到 `branch_history`。必须先核对结果、最新要求及原状态，在正文交付临时结果或说明取消，再接回原事项。新信息影响原决定时，必须只更新受影响部分，禁止预记正文已交付。恢复点缺失时必须从可用对话或摘要补查，禁止猜测。

原任务明确暂停时，处理临时事项前必须确认用户另行要求该事项且未暂停全部工作，再填写 `allow_while_paused:true` 和实际用户消息 `allow_while_paused_source`。接回后原任务必须保持暂停。临时事项被用户暂停后恢复时必须提供 `resume_source`。原状态存在结构或执行门槛错误时，必须在恢复原任务前处理 `original_state_errors`。独立且获准的临时请求可继续。恢复时无需传两份完整状态，已有 `previous` 时仍可用于原有跨轮检查。脚本只读并返回结果。记录和授权必须取自实际来源。

操作正在运行或结果未知时，可用 `operations` 保存其 `id`、实际 `reference`、`status`、`side_effect` 和 `blocks_next`。`blocks_next` 和 `blocks_completion` 必须分别对应实际下一动作和最终完成的依赖。`side_effect` 用于判断结果未知时能否安全重试。同一操作必须沿用原标识及引用。`check_operation` 仅核实原操作，在查询权限内可进行，即使后续执行许可缺失。必须处理已有结构错误，查明后继续或重试仍必须有有效授权。`blocks_next:true` 的操作已失败时，脚本先返回 `handle_operation_failure`。禁止用等待状态遮蔽失败。

### 操作结果与依赖

更新操作结果或依赖时，必须提交实际 `previous`，也可使用已有有效快照的增量输入。结果或完成依赖有新观察时，必须更新 `evidence`。若证据来源地址未变，可保留 `evidence`，并必须用可核对的新结果位置、版本或观测记录填写 `evidence_revision`。新旧状态使用的来源和版本必须分别对应当时的实际观察。

只读操作尚无结果，而新证据表明实际下一动作可独立推进时，必须在 `next_dependency_evidence` 记录该证据，更新 `blocks_next` 并保留原操作。下一动作变化后，必须按实际依赖重新核对。必须单独核对完成依赖，解除 `blocks_completion` 必须遵守[恢复规则](state-recovery.md#中断恢复)。有副作用且结果未知时，必须保留原有阻塞，已获准的独立工作可按下一段推进。失败结果必须按异常处理。检查器比较相邻快照，比较 `evidence_revision` 和 `next_dependency_evidence` 时忽略空白字符。主控必须核查证据来源和较早记录，确认标识属于本次实际观察，且能证明相应结果、处置或依赖变化。

主控必须在[独立动作与授权限制](../SKILL.md#不可短路主控)内按脚本返回的下一动作推进。主任务执行受阻且计划和目标已满足展示门槛时，只读 `independent_action` 必须明确动作并设置 `independent_action_read_only:true`。可能产生业务副作用的动作必须已有有效 `execution_receipt`、完整 `gates`、执行范围和许可动作，否则禁止返回 `continue_local`。返回 `continue_local` 时必须保留原阻塞原因。未填 `independent_action`，且计划已展示、目标未展示、本轮不限于局部时，必须核对当前范围及确认依据。允许补齐时必须按[正式计划正文检查](#正式计划正文检查)同轮展示计划和目标，禁止把路由当作授权。临时事项受阻时必须保持等待。

讨论中的待决项、收口问答与首次正式展示必须遵守[收口规则](#首次从讨论转入计划)，有无计划请求均适用。确有缺口且用户请求草案时，可交付标明缺口的讨论稿。用户明确限定本轮只展示计划或验收目标其中一项时，必须说明两者必须同轮展示，并等待用户调整限定。禁止用旧草案的待核实状态阻拦已满足条件的正式展示。计划展示后的执行确认必须遵守[首次执行的确认顺序](#首次执行的确认顺序)。

执行中准备继续实际操作时，覆盖尚未核对或仍有影响方案的待决项，必须先按脚本提示修正状态并处理缺口。已完成的本轮局部动作可按限定收口。有 `running` 或 `unknown` 且 `blocks_next:true` 的操作时，必须先核实。操作失败时，脚本返回 `handle_operation_failure`，必须先分类处理。有此类阻塞操作时，必须先核实该操作已成功，再进入 `local_complete`。必须遵从用户暂停或本轮范围限定。结果未知且可能有副作用时必须先核实原操作，禁止盲目重试。

### 跨轮状态核对

目标展示后进入执行、验证、审查或完成时，必须传入 `{"previous":上一状态,"state":当前状态}`，核对当前范围与上一快照及实际变化。缺少上一状态时，脚本返回 `repair_state`，禁止将新目标直接送入 `next` 或 `check` 当作已通过。计划请求撤回、暂停恢复或决定变化等其他情况，需要跨轮检查时也必须传入实际上一状态。此时输出 `scope: structure_and_changes`。`decided`、`delegated` 和 `excluded` 的变更及删除，必须核对来源和继续使用原授权的影响。同一事项在有效委托内调整实际决定时，可复用原来源，并必须在现有 `impact_review.reason` 说明委托范围及影响，无需另索授权。若本次计划已在上一状态实际交付、本轮才清除请求，`plan_request_delivery_source` 必须指向本次实际交付。禁止用旧计划冒充新请求的交付。

`scope: structure_only` 表示只检查结构。来源是否真实、决定是否理解正确、问题是否覆盖完整、消息是否实际送达，都必须由主控核对。脚本无法强迫模型调用。消息记录文件不可访问时，可依据可用对话判断下一步。证据无法核实时，必须保留未知，禁止用普通文件冒充宿主回执。原有摘要的写入、并发和恢复必须遵守[记录模块](state-recovery.md)。检查器不会替换摘要文件。
