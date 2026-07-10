# Verification Counterexamples

这些反例命中时，不得宣称完成，必须回到 verification 分类或上游阶段。

## 窄验证冒充全通过

- 错误：只跑了一个局部测试或只看了 diff，就说全部完成。
- 违规：证据覆盖不足，不能支撑全部 AC。
- 回退：逐条 AC 标注 evidence_strength；未覆盖项只能 Partial、Not met 或 Blocked。

## 未运行 plan 验证命令

- 错误：计划要求运行测试、lint 或 build，但最终报告只写“未运行，应该没问题”。
- 违规：没有 fresh verification evidence。
- 回退：运行命令；无法运行时记录原因、替代证据和 AC 影响。

## 过期证据当新证据

- 错误：引用旧会话、旧日志或修改前的测试结果作为本轮通过证据。
- 违规：stale evidence 不能支撑完成声明。
- 回退：重新获取本轮证据；无法获取则标 Blocked 或 Partial。

## 跳过用户验收门

- 错误：VerificationReport 写完后直接说“已交付完成”，没有 `delivery_acknowledged_by_user` 状态。
- 违规：跳过 User Acceptance Gate。
- 回退：状态置为 `awaiting_user_acceptance`，等待用户 accept / reject / partial-accept。

## 未自检就请求用户验收

- 错误：直接输出“用户验收门禁：等待用户验收，是否接受这个交付？”，但没有逐项自检 Plan tasks、Review reports、AC coverage、Verification strategy、Scope drift、Quality gate 和 Residual risk。
- 违规：User Acceptance Gate 只能在验收前自检完成且无 fail 后触发；用户不负责替 agent 发现没自检。
- 回退：回到 verification，完成验收前自检表；若发现 fail，按 executing / blocked / plan-revision / brainstorming 路由，不得继续要求用户 accept。

## 用户提醒后才自检

- 错误：用户问“你做自检了吗”，agent 才开始逐项检查。
- 违规：自检是进入 User Acceptance Gate 的前置条件，不是用户追问后的补救动作。
- 回退：撤回 awaiting_user_acceptance 状态，完成验收前自检和 VerificationReport 更新后，再决定是否重新进入 User Acceptance Gate。

## 文件存在冒充功能完成

- 错误：目标是新增功能、迁移流程或优化协议，验证只检查目标文件存在或新增文字存在。
- 违规：文件存在只能证明写入，不能证明功能、流程或规则生效。
- 回退：补功能级验证，例如测试、命令、样例任务、walkthrough、反例检查或人工审查表；无法补强时状态最多 partial / blocked。

## 文本命中冒充契约通过

- 错误：用 `rg "scope_denominator"` 或 `rg "Target Coverage"` 命中，就说目标门禁已完成。
- 违规：文本存在不等于语义正确，也不证明门禁能拦住旧问题。
- 回退：补语义级检查或反例样例，证明缺目标分母、Phase 粗拆、弱证据包装完成等问题会被拦截。

## 只验证主路径

- 错误：只验证正常路径或一个成功样例，忽略错误路径、边界、反例、目标分母剩余单元。
- 违规：精打磨和生产级任务不能用主路径证据支撑完整完成；完整 / 100% 目标必须覆盖分母。
- 回退：补边界验证、反例验证和 Target coverage；无法补齐时标 partial / blocked。

## 自检循环假闭环

- 错误：自检发现问题后只改文字，再跑同一个粗检查并宣布闭环。
- 违规：没有证明原问题类型被消除，自检优化循环没有复验证据。
- 回退：记录 finding、route、fix、recheck 和 evidence_strength；用功能级证据或反例样例证明问题已消除。

## 未覆盖目标单元仍请求验收

- 错误：VerificationReport.coverage 覆盖了部分 AC，但 scope_denominator 中仍有目标单元没有 target_coverage，就进入 User Acceptance Gate。
- 违规：目标覆盖是验收前自检的一部分；未覆盖目标单元不得请求用户验收完整交付。
- 回退：回到 executing、plan-revision、brainstorming 或 blocked；补齐 target_coverage 后再判断是否可验收。

## 失败后默认回执行

- 错误：验证失败后直接继续改代码，没有判断是 executing、blocked、partial、plan-revision 还是 brainstorming。
- 违规：失败未分类，容易盲修。
- 回退：先分类并写入 Iteration Log，再选择下一状态。
