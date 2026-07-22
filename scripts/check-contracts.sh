#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

fail() {
  printf 'check-contracts: %s\n' "$1" >&2
  exit 1
}

require_file() {
  local path="$1"
  [[ -f "$path" ]] || fail "missing required file: $path"
}

require_match() {
  local pattern="$1"
  local path="$2"
  rg -q -- "$pattern" "$path" || fail "missing pattern in $path: $pattern"
}

forbid_match() {
  local pattern="$1"
  local scope="$2"
  local tmp
  tmp="$(mktemp)"
  if rg -n -- "$pattern" $scope >"$tmp"; then
    cat "$tmp" >&2
    rm -f "$tmp"
    fail "forbidden pattern found: $pattern"
  fi
  rm -f "$tmp"
}

require_file SKILL.md
require_file README.md
require_file CLAUDE.md
require_file references/quick-start.md
require_file references/faq.md
require_file references/scenarios.md
require_file VERSION.md
require_file tests/dialogue-contracts/explicit-discussion-request.md
require_file tests/dialogue-contracts/discussion-transition.md
require_file tests/dialogue-contracts/plan-with-implementation.md
require_file tests/dialogue-contracts/acceptance-goal-discussion.md
require_file tests/dialogue-contracts/end-to-end-small-case.md
require_file tests/dialogue-contracts/user-acceptance-handoff.md
require_file tests/dialogue-contracts/task-splitting.md
require_file tests/dialogue-contracts/exception-routing.md
require_file tests/dialogue-contracts/retry-strategy-change.md
require_file tests/dialogue-contracts/unified-exception-notice.md
require_file tests/dialogue-contracts/progressive-doc-routing.md
require_file tests/dialogue-contracts/deferred-goal-tools.md

DOC_SCOPE='SKILL.md README.md CLAUDE.md references/quick-start.md references/faq.md references/scenarios.md'

# 主流程必须先讨论，再输出计划和最终验收目标。
require_match '仔细询问并逐项讨论' SKILL.md
require_match '输出计划' SKILL.md
require_match '讨论并确认计划' SKILL.md
require_match '讨论验收目标' SKILL.md
require_match '输出并确认验收目标' SKILL.md
require_match '创建目标并执行' SKILL.md
require_match '未达标或无法确认达标时先分类' SKILL.md
require_match '可修复问题打回修复，最多 3 次；其他异常进入对应路径' SKILL.md

# 讨论阶段不能被完整草案替代。
require_match '每轮只处理一个具体决策点' SKILL.md
require_match '已确认事实' SKILL.md
require_match '待确认建议' SKILL.md
require_match '已确认决定' SKILL.md
require_match '用户选择生成计划前，不得输出完整计划' SKILL.md
require_match '继续讨论，或结束讨论并生成计划' SKILL.md
require_match '普通“确认”“继续”“可以”' SKILL.md

# 计划必须说明实施方法，并以已确认事项为顶层结构。
require_match '顶层计划事项必须按照已确认的需求或问题组织' SKILL.md
require_match '### 已确认' SKILL.md
require_match '### 实施方案' SKILL.md
require_match '### 涉及位置' SKILL.md
require_match '### 内部验证' SKILL.md
require_match '需要合并或拆分时，必须说明来源和原因' SKILL.md
require_match '不能把模型偏好偷偷写入计划' SKILL.md
require_match '不计作新的用户需求或问题' SKILL.md

# 最终验收目标必须先讨论、最小化并原样进入目标模式。
require_match '用户选择生成前，不得输出完整验收目标草案' SKILL.md
require_match '对每个候选目标进行删除判断' SKILL.md
require_match '不强制表格，也不设置固定条数' SKILL.md
require_match '不得按文件、模块、测试场景或实施步骤拆分最终目标' SKILL.md
require_match '原样进入目标模式' SKILL.md
require_match '不能增加工程目标、改变粒度或重新解释' SKILL.md

# Deferred 目标工具必须先加载 schema，并与宿主任务形成状态闭环。
require_match 'ToolSearch query="select:TaskCreate"' SKILL.md
require_match 'ToolSearch query="select:TaskList"' SKILL.md
require_match 'ToolSearch query="select:TaskUpdate"' SKILL.md
require_match 'Invalid tool parameters' SKILL.md
require_match '禁止重复创建' SKILL.md
require_match '保存宿主返回的目标或任务 ID' SKILL.md
require_match 'TaskUpdate.*更新为执行中' SKILL.md
require_match 'TaskUpdate.*同步任务状态' SKILL.md
require_match '为什么调用 TaskCreate 会连续出现 Invalid tool parameters' references/faq.md
require_match '为什么工作完成了，宿主任务仍然显示未完成' references/faq.md
require_match '宿主任务只映射最终验收目标' README.md
require_match '实施步骤不创建为宿主任务' tests/dialogue-contracts/deferred-goal-tools.md
require_match '工作完成后只更新内部状态，不调用 `TaskUpdate`' tests/dialogue-contracts/deferred-goal-tools.md
require_match '中断恢复或调用失败后重复创建相同任务' tests/dialogue-contracts/deferred-goal-tools.md

# 执行、权限、恢复和质量闭环仍然保留。
require_match '不默认新建分支' SKILL.md
require_match '不自动合并临时分支' SKILL.md
require_match '工程测试只能作为辅助检查' SKILL.md
require_match '质量判断' SKILL.md
require_match '质量判断只分两档' SKILL.md
require_match '达标：满足最终验收目标' SKILL.md
require_match '未达标：没有满足最终验收目标' SKILL.md
require_match '发现任何瑕疵都必须判断为“未达标”' SKILL.md
require_match '### 用户验收补位' SKILL.md
require_match '必须明确通知“需要用户验收”' SKILL.md
require_match '验收步骤必须针对当前目标编写' SKILL.md
require_match '用户无法完成必要验收且没有其他可靠证据时' SKILL.md
require_match '不得在必要的用户验收尚未返回结果时标记目标完成' SKILL.md
require_match '高风险复核' SKILL.md
require_match '大任务写入规则' SKILL.md
require_match '轻量计划摘要' SKILL.md
require_match '\.task-driver/\{任务标题\}-\{YYYYMMDDHHmmss\}-计划摘要\.md' SKILL.md

# 任务规模必须按业务关系判断，拆分范围由用户确认。
require_match '任务规模与拆分边界' SKILL.md
require_match '业务目标、权限、风险、交付和回滚关系' SKILL.md
require_match '不按固定文件数、计划项数或验收目标数机械判断' SKILL.md
require_match '模型先说明拆分依据、建议的第一批范围和延期事项，再让用户确认本轮范围' SKILL.md
require_match '轻量计划摘要' SKILL.md
require_match '模型只请用户确认本轮范围' tests/dialogue-contracts/task-splitting.md

# 四类异常路由与修复策略变化不可回退。
require_match '### 异常分类' SKILL.md
require_match '可修复：' SKILL.md
require_match '需要用户验收：' SKILL.md
require_match '需要用户授权或决定：' SKILL.md
require_match '受阻：' SKILL.md
require_match '非可修复异常不得为了凑次数重复执行' SKILL.md
require_match '每次修复必须改变实施策略或修复内容' SKILL.md
require_match '停止机械重试' SKILL.md
require_match '后三类异常不消耗最多 3 次的修复次数' tests/dialogue-contracts/exception-routing.md
require_match '下一次修复改变实施策略或修复内容' tests/dialogue-contracts/retry-strategy-change.md

# 异常通知只保留决策所需信息；用户操作必须可执行、可判断。
require_match '### 统一异常通知' SKILL.md
require_match '当前结果：' SKILL.md
require_match '原因：' SKILL.md
require_match '已完成：' SKILL.md
require_match '下一步：' SKILL.md
require_match '不粘贴长日志或内部状态转储' SKILL.md
require_match '编号验收步骤和每步预期结果' tests/dialogue-contracts/unified-exception-notice.md
require_match '明确通过条件和反馈要求' tests/dialogue-contracts/unified-exception-notice.md

# FAQ、场景指南和渐进式入口各自承担独立职责。
require_match '## 文档导航' README.md
require_match 'references/quick-start.md' README.md
require_match 'references/faq.md' README.md
require_match 'references/scenarios.md' README.md
require_match '不要求每次任务无条件加载全部参考文件' SKILL.md
require_match '## 三次修复是必须执行三次吗' references/faq.md
require_match '## 怎样判断任务是否应该拆分' references/faq.md
require_match '## 低风险 Bug 修复' references/scenarios.md
require_match '## 新功能或新模块建设' references/scenarios.md
require_match '## 跨模块重构' references/scenarios.md
require_match '## 生产配置、外部接口或费用任务' references/scenarios.md
require_match '## UI、设备体验或主观质量任务' references/scenarios.md
require_match '场景建议不能代替用户决定' references/scenarios.md
require_match '各文档只承担自己的职责，不大段复制完整协议' tests/dialogue-contracts/progressive-doc-routing.md

# 面向用户的说明必须与主协议一致。
require_match '仔细询问并逐项讨论' README.md
require_match '每个计划事项必须展示“已确认”和“实施方案”' README.md
require_match '计划确认后先讨论最终结果' README.md
require_match '用户确认后的目标原样进入目标模式' README.md
require_match '需要用户验收时' README.md
require_match '当前版本：v0.9.3' README.md
require_match '仔细询问并逐项讨论' CLAUDE.md
require_match '最终验收目标必须先逐项讨论' CLAUDE.md
require_match '任务规模必须按业务目标、权限、风险、交付和回滚关系判断' CLAUDE.md
require_match '只有可修复问题进入最多 3 次的修复循环' CLAUDE.md
require_match '逐项讨论' references/quick-start.md
require_match '计划包含实施方案' tests/dialogue-contracts/plan-with-implementation.md
require_match '五项目标覆盖' tests/dialogue-contracts/end-to-end-small-case.md
require_match '模型一次只讨论一个问题' tests/dialogue-contracts/end-to-end-small-case.md
require_match '提供继续讨论或生成计划的选择' tests/dialogue-contracts/end-to-end-small-case.md
require_match '每项展示已确认决策和实施方案' tests/dialogue-contracts/end-to-end-small-case.md
require_match '模型逐项讨论两个问题的最终完成状态' tests/dialogue-contracts/end-to-end-small-case.md
require_match '输出两个与原问题对应的必要终极目标' tests/dialogue-contracts/end-to-end-small-case.md
require_match '用户确认后原样创建目标并执行' tests/dialogue-contracts/end-to-end-small-case.md
require_match '用户验收补位' tests/dialogue-contracts/user-acceptance-handoff.md
require_match '用户反馈前不把目标标记为已达成或达标' tests/dialogue-contracts/user-acceptance-handoff.md

# 防止旧的“先输出表格草案再讨论”协议回退。
forbid_match '必须使用轻量表格' "$DOC_SCOPE"
forbid_match '计划确认只代表“可以进入验收标准草案”' "$DOC_SCOPE"
forbid_match '够用|有瑕疵|不够用' "$DOC_SCOPE"
forbid_match '仔细询问[[:space:]]*$' 'README.md CLAUDE.md references/quick-start.md'
forbid_match 'SpecPacket|PlanPacket|TaskResult|ReviewReport|VerificationReport|GoalDraft' "$DOC_SCOPE"
forbid_match 'gate_mode|execution_mode|brainstorming|planning|executing|verification' "$DOC_SCOPE"
forbid_match 'approved spec|approved plan|Acceptance Criteria|Target Coverage Matrix|Decomposition Strategy|File Map' "$DOC_SCOPE"
forbid_match '\.task-driver/(specs|plans|ledgers)' "$DOC_SCOPE"

printf 'check-contracts: ok\n'
