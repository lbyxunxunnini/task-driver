#!/usr/bin/env bash
# 文档结构、约束入口与本地链接检查；不证明真实模型或宿主行为通过。
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

fail() { printf 'check-contracts: %s\n' "$1" >&2; exit 1; }
require_file() { [[ -f "$1" ]] || fail "missing required file: $1"; }
require_match() { rg -q -- "$1" "$2" || fail "missing constraint in $2: $1"; }
check_patterns() {
  local file="$1"
  shift
  local pattern
  for pattern in "$@"; do require_match "$pattern" "$file"; done
}
forbid_match() {
  local pattern="$1"
  shift
  if rg -n -- "$pattern" "$@"; then
    fail "retired protocol found: $pattern"
  else
    local result=$?
    [[ "$result" == 1 ]] || fail "cannot scan retired protocol: $pattern"
  fi
}

# 每个判断有单一归属；只检查模块入口和必要约束，不把文本匹配当行为验收。
for file in SKILL.md README.md VERSION.md .skillhub.json CHANGELOG.md references/quick-start.md \
  references/faq.md references/scenarios.md references/templates.md \
  references/analysis.md references/discussion.md references/planning.md references/goals.md \
  references/execution.md references/subagents.md references/verification.md references/review.md references/state-recovery.md; do
  require_file "$file"
done
require_file scripts/workflow_control.py
require_file scripts/build-package.sh
require_file references/workflow-control.md
require_file tests/workflow-control/test_workflow_control.py
check_patterns SKILL.md '仅由用户显式调用' '不因任务复杂而自动启用' '不另设轻量模式'
check_patterns README.md '仅由用户显式调用' 'scripts/build-package.sh' '子代理你决定'
for name in explicit-discussion-request discussion-transition plan-with-implementation \
  acceptance-goal-discussion end-to-end-small-case user-acceptance-handoff task-splitting \
  exception-routing retry-strategy-change unified-exception-notice progressive-doc-routing \
  deferred-goal-tools visible-reply-boundary research-and-questioning review-authority-summary \
  exhaustive-discussion discussion-continuity-dedup state-recovery nine-corrections decision-driven-transition routing-control subagent-scheduling \
  progress-anchor addressable-summary design-doc-is-not-plan; do
  require_file "tests/dialogue-contracts/$name.md"
done
check_patterns SKILL.md '^## 状态与主控职责' '^## 阶段转换' '^## 展示与确认策略' \
  '^## 确认与授权' '^## 完成门槛' '已有完整授权必须复用' \
  '链接不是递归加载指令' '动作前核对条件' '根据实际结果更新'  \
  '同一场景可展示边界清楚的完整方案' \
  '讨论中的局部请求完成后' '讨论阶段的最终回复必须以一个问题结束' '仅有阶段标记、总结或继续的承诺不算续接' '必须调用\[轻量检查\]' '计划与目标必须同轮展示' '等待用户调整限定' \
  '用户要求单独处理另一件事' '局部调整，默认只展示新增、修改或删除的条目' \
  '用户只授权审查子代理时不扩大为执行分派' '结果未知的副作用操作先核实' \
  '执行，开启子代理' '执行，不开启子代理' '不执行，继续讨论' 'references/subagents.md' \
  '进度锚点' '只读检查代理' '不得写成已独立检查' \
  '四项可追溯证据' '四项引证' '四项缺一不可' '不构成任何一项内容确认' \
  '计划已在对话中实际展示或摘要展示' '用户确认该计划内容' '用户确认最终验收目标' \
  '执行范围具有用户授权' '确认与授权须能回溯到实际用户消息' \
  '明确委托模型在该范围内决定' '明确表示不需要该阶段确认' \
  '进入执行前目标也须实际展示' '可直接判断的最终结果或通过条件' '不含笼统的' \
  '明确委托模型/表示不需要该阶段确认' '在请求中写明可直接判断的最终结果或通过条件' \
  '子代理设置优先采用用户明确选择' '用户明确委托模型决定时由模型' \
  '用户明确限定本轮只交付指定内容' 'superseded' 'semantic_review' 'goals.included' 'evidence_map' \
  'completion_basis' 'unverified_goals' \
  '有记录来源且未变化的已确认条件不重走' '调用本 skill 表示按固定链路推进'
check_patterns references/analysis.md '用户目标 → 实际使用过程' '不等于删除支付覆盖' \
  '未知条件若会改变' '不编造调查结果' '已核实的原有情况' '候选方案' '明确委托模型决定调查代理'
check_patterns references/discussion.md '^## 回答后的推进' '^## 讨论完成门禁' '^## 决策项与提问' '仅更新原话实际覆盖的内容' \
  '不是否定、不可用、取消或委托' '覆盖核对' '决定核对' '讨论阶段把回复交还用户时，最终回复必须以一个问题结束' \
  '先保存本轮有效变化，再问下一项' '未满足执行入口条件时，不得开始实际执行' \
  '^### 提问语义复核' 'semantic_review' 'not_already_decided' 'not_delegated' 'transition_intent' 'no_user_question' \
  'incomplete_plan_delivered'
check_patterns references/planning.md '### 已确认' '### 实施方案' '核心机制' \
  '具体实施方案' '长计划'
check_patterns references/goals.md '目标来自需求' '删除判断' '通过条件' \
  '不得从自选施工步骤反推目标' '^### 目标拆分与证据映射' 'included' 'excluded' 'evidence_map' \
  'changed' 'associated' 'completion_basis' 'completion_report' 'unverified_goals' \
  'reason' 'impact' 'goal_scope_baseline' 'superseded_goals' 'local_goal_id'
check_patterns references/execution.md '^### 执行入口' '主控四项证据' '不得开始实施' \
  '不得先创建宿主目标再补引证' '实际工具、schema 和使用限制' '不尝试不允许的调用' 'select:TaskCreate' 'select:TaskList' \
  'select:TaskUpdate' 'Invalid tool parameters' '重试一次' '必须先查询已有任务' \
  '禁止重复创建' '保存返回 ID' '两类工具均不可用或不允许才在对话中跟踪' \
  '每条目标只对应一条任务' '先更新执行中' 'subagents.md' 'superseded' 'local_goal_id'
check_patterns references/subagents.md '^## 选择执行方式' '^## 并发准入与依赖' \
  '^## 分派与交接' '^## 运行调度与异常接管' '^## 整合与审查交接' \
  '安全独立只是准入条件' '不以安全条件满足强制分派' '当前就绪任务' \
  '不同时修改同一内容' '不争用会相互干扰的运行资源' '不假定前序结果' \
  '执行或审查代理须取得对应授权' '只授权审查时不扩大为执行分派' '明确委托模型决定执行设置' \
  '执行入口' '不得作为额外的宿主验收任务创建' '不另建管理代理' \
  '不重复代理正在做的任务' '停止请求不是已停止的证据' '结果未知' \
  '不作为该产物的独立复核者' '次数均由审查模块唯一维护'
check_patterns references/verification.md '静态检查可以直接证明文本类目标' \
  '实际输入' '观察结果' '不把旧快照结果拼成新版本通过' \
  '判据留在测试侧' '反馈不通过' '受阻' '当前有效目标' 'semantic_review' \
  'goals.included' 'goals.evidence_map' 'goals.excluded' 'completion_basis:user_requested' 'unverified_goals'
check_patterns references/review.md '无论是否开启子代理' '主模型审查实际交付' \
  '不得新增标准或超出检查范围' '需要用户验收' '需要用户授权或决定' \
  '同一最终目标最多修复 3 次' '最后一次允许的修复后仍必须完成复验' \
  '用户明确指定本任务循环上限' '首审和复审均使用独立上下文' '预审通过不等于整项目标达成' \
  '禁止执行者自评和前次审查结论' '无法判断：审查输入不合规' \
  '不得删改原审查报告' '独立审查最多 3 次' '未受影响的有效证据可复用' \
  '当前有效目标' '用户明确委托模型决定子代理设置'
check_patterns references/state-recovery.md '同一任务仅一份' '10 次用户回答' \
  '先保存并核对成功' '保存后再提问' '长计划开始执行前' \
  '步骤全部打勾不等于目标达成' '结果未知先核查' '终端断开不代表进程停止' \
  '不盲目重试' '不重置|次数继续有效' '不保存凭据或秘密' '本轮记录“正文待交付、状态待同步”' \
  '^## 引用与展开' '^## 局部插入与恢复' '^## 进度锚点' '不保留悬空引用' \
  '每 3 个阶段结果最多 1 次' '阶段结果指' 'A\{n\}' '不得把锚点写成已独立检查' \
  '不产生或恢复子代理授权' 'included' 'excluded' 'evidence_map'
check_patterns references/workflow-control.md 'interruptions' 'reconcile_interruption' \
  'resume_point' 'original_state_errors' '`final`' 'draft_reply' 'discussion_handoff' \
  '最后一条非空正文是一个问题' 'scope_limited' 'handle_operation_failure' \
  'scope_complete' 'superseded_goals' 'host_goal_sync' 'semantic_review' \
  '不再要求逐字复制' '不能判断问题是否扣题' 'goals.presented:true' 'plan.presented' \
  'review_id' 'authorization_source' 'presentation_id' 'incomplete_plan_delivered' \
  'goals.included' 'goals.excluded' 'goals.evidence_map' 'completion_basis' 'unverified_goals' \
  'goal_scope_baseline' 'local_goal_id' 'host_id' '不能被等待状态遮蔽'
check_patterns references/subagents.md '^## 只读检查代理' '^## 提问语义复核代理' '不冒称已检查' \
  '不产生或恢复子代理授权' '不能消除与主控同模型' '不计入修复次数与独立复核次数' \
  'reviewer: independent' 'reviewer: main'
check_patterns references/review.md '属于执行途中的只读路线复查'
check_patterns references/templates.md '进度锚点交接模板' '引用与展开' '四项引证' \
  '\| 编号（如 F1） \|' '\| 编号（如 D1） \|' '\| 编号（如 G1） \|' \
  'included' 'excluded' 'source' 'evidence_map' 'goal_scope_baseline' 'completion_basis' 'completion_report' 'unverified_goals' \
  'local_goal_id'
check_patterns tests/dialogue-contracts/progress-anchor.md '不触发' '阶段结果' '不恢复子代理授权'
check_patterns tests/dialogue-contracts/discussion-transition.md '最终提问门禁' '回答后仍有影响方案的待决项' \
  '最后一条实质内容不再是问题' '明确限定本轮只交付指定内容' \
  '`discussion_handoff` 使用 `decision`' '`discussion_handoff` 使用 `plan_transition`' \
  'semantic_review' '不是唯一合法措辞' '方案 A 值得做' '评价不等于选择'
check_patterns tests/dialogue-contracts/acceptance-goal-discussion.md 'evidence_map' \
  'evidence_map 证据' 'superseded' 'completion_basis:user_requested' 'completion_report' 'unverified_goals'
check_patterns tests/dialogue-contracts/end-to-end-small-case.md 'evidence_map'
check_patterns tests/dialogue-contracts/routing-control.md '用户明确“本轮只交付计划与目标或其他指定局部内容”' \
  '先返回 `check_operation`'
check_patterns tests/dialogue-contracts/deferred-goal-tools.md '用户变更目标或接受部分结果' \
  '将旧目标标记为 `superseded`' '不因宿主限制把用户已接受的结果改写成受阻' 'local_goal_id'
check_patterns tests/dialogue-contracts/research-and-questioning.md '明确委托模型决定调查代理'
check_patterns references/quick-start.md '不是唯一合法文本' 'semantic_review' 'included' 'excluded' 'evidence_map' \
  'goal_scope_baseline' '来源：用户要求'
check_patterns tests/dialogue-contracts/addressable-summary.md '记录编号' '用户选项'
check_patterns tests/dialogue-contracts/design-doc-is-not-plan.md '创建执行目标' '只更新该决定' \
  '文档存在不等于计划已展示' '不用给我看计划' '目标不用确认' '完成/做好/第一版' \
  '可直接判断的结果' '把执行意图或文档引用写进计划、目标证据' '越权执行'
check_patterns references/templates.md '用户原话或消息来源' '实际确认或委托的内容' '恢复后第一步' \
  '当前事项及未答部分' '产物版本' '第七步|独立复核要求' '末尾仅询问尚缺的确认'
check_patterns references/scenarios.md '多轮正反例' '环境恢复' '创作设计' '测试方案' \
  '执行中澄清后继续' '未知不等于取消'
check_patterns README.md '## 30 秒选择器' '## 文档导航' '## 当前版本' '## 本版改进' \
  'included' 'excluded' 'goal_scope_baseline' '来源：用户要求'
forbid_match '只请用户决定关键缺口|关键事项闭合后停止挖问题|不要求穷尽全部潜在问题' SKILL.md references/*.md
forbid_match 'SpecPacket|PlanPacket|TaskResult|ReviewReport|VerificationReport|GoalDraft' SKILL.md references/*.md
forbid_match '补齐正文后立即结束本轮|禁止展开后续需求清单' SKILL.md references/*.md
forbid_match '结束讨论并生成计划（推荐）' references/quick-start.md
forbid_match '请求确认结束讨论并生成计划|是否结束讨论并生成计划' SKILL.md references/*.md tests/dialogue-contracts/discussion-transition.md
forbid_match '以下条件全部满足时，必须拆分并发|必须由主线程串行执行|八模块|八个职责模块' SKILL.md README.md references/*.md

# 本地路径和标题锚点是真实引用检查；只扫描维护中的文档，不改写历史报告。
python3 - <<'PY'
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

root = Path.cwd()
docs = [Path("SKILL.md"), Path("README.md")]
docs += sorted(Path("references").glob("*.md"))
docs += sorted(Path("tests/dialogue-contracts").glob("*.md"))

def prose(text):
    fence = None
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith((chr(96) * 3, "~" * 3)):
            marker = stripped[0]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            continue
        if fence is None:
            yield line

def anchors(path):
    used = {}
    result = set()
    for line in prose(path.read_text(encoding="utf-8")):
        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        title = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", match.group(1))
        slug = re.sub(r"[^\w -]", "", title.lower()).replace(" ", "-")
        number = used.get(slug, 0)
        used[slug] = number + 1
        result.add(slug if number == 0 else f"{slug}-{number}")
    return result

errors = []
checked = 0
cache = {}
for doc in docs:
    for line_number, line in enumerate(prose(doc.read_text(encoding="utf-8")), 1):
        for href in re.findall(r"\[[^]\n]+\]\(([^)\n]+)\)", line):
            href = href.strip().strip("<>")
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc:
                continue
            target = (doc.parent / unquote(parsed.path)).resolve() if parsed.path else doc.resolve()
            if not target.is_file():
                errors.append(f"{doc}: local link target missing: {href}")
                continue
            if parsed.fragment:
                if target not in cache:
                    cache[target] = anchors(target)
                if unquote(parsed.fragment) not in cache[target]:
                    errors.append(f"{doc}: heading anchor missing: {href}")
            checked += 1

version = Path("VERSION.md").read_text(encoding="utf-8").strip()
markers = re.findall(r"^当前版本：(\S+)\s*$", Path("README.md").read_text(encoding="utf-8"), re.M)
if markers != [version]:
    errors.append("README current version does not match VERSION.md")

if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)
print(f"check-contracts: local links ok ({checked})")
PY

printf 'check-contracts: ok (static constraints; not a model replay)\n'
