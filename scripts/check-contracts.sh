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
for file in SKILL.md README.md VERSION.md .skillhub.json references/quick-start.md \
  references/faq.md references/scenarios.md references/templates.md \
  references/analysis.md references/discussion.md references/planning.md references/goals.md \
  references/execution.md references/verification.md references/review.md references/state-recovery.md; do
  require_file "$file"
done
for name in explicit-discussion-request discussion-transition plan-with-implementation \
  acceptance-goal-discussion end-to-end-small-case user-acceptance-handoff task-splitting \
  exception-routing retry-strategy-change unified-exception-notice progressive-doc-routing \
  deferred-goal-tools visible-reply-boundary research-and-questioning review-authority-summary \
  exhaustive-discussion state-recovery nine-corrections decision-driven-transition routing-control; do
  require_file "tests/dialogue-contracts/$name.md"
done
check_patterns SKILL.md '^## 状态与主控职责' '^## 阶段转换' '^## 展示与确认策略' \
  '^## 确认与授权' '^## 完成门槛' '已有完整授权必须复用' \
  '链接不是递归加载指令' '动作前核对条件' '根据实际结果更新'  \
  '每轮最多一个独立回答请求' \
  '用户只授权审查子代理时不扩大为执行分派' '结果未知的副作用操作先核实' \
  '执行，开启子代理' '执行，不开启子代理' '不执行，继续讨论'
check_patterns references/analysis.md '用户目标 → 实际使用过程' '不等于删除支付覆盖' \
  '未知条件若会改变' '不伪装|不得伪装'
check_patterns references/discussion.md '^## 回答后的推进' '^## 讨论完成门禁' '^### 先形成决策项' '^### 再生成并检查当前问题' \
  '变量名与裸取值' '自由输入提示' \
  '不是否定、不可用、取消或委托' '覆盖核对' '决定核对' \
  '先保存本轮有效变化，再问下一项'
check_patterns references/planning.md '### 已确认' '### 实施方案' '核心机制' \
  '具体实施方案' '长计划'
check_patterns references/goals.md '目标来自需求' '删除判断' '通过条件' \
  '不得从自选施工步骤反推目标'
check_patterns references/execution.md '^### 执行入口' '实际工具和 schema' 'select:TaskCreate' 'select:TaskList' \
  'select:TaskUpdate' 'Invalid tool parameters' '重试一次' '必须先查询已有任务' \
  '禁止重复创建' '保存返回 ID' '两类工具均不可用才在对话中跟踪' \
  '每条目标只对应一条任务' '先更新执行中' '必须由主线程串行执行' \
  '以下条件全部满足时，必须拆分并发' '关闭子代理时，禁止启用执行子代理'
check_patterns references/verification.md '静态检查可以直接证明文本类目标' \
  '实际输入' '观察结果' '不把旧快照结果拼成新版本通过' \
  '判据留在测试侧' '反馈不通过' '受阻'
check_patterns references/review.md '无论是否开启子代理' '主模型审查实际交付' \
  '不得新增标准或超出检查范围' '需要用户验收' '需要用户授权或决定' \
  '同一最终目标最多修复 3 次' '最后一次允许的修复后仍必须完成复验' \
  '用户明确指定本任务循环上限' '首审和复审均使用独立上下文' \
  '禁止执行者自评和前次审查结论' '无法判断：审查输入不合规' \
  '不得删改原审查报告' '独立审查最多 3 次' '未受影响的有效证据可复用'
check_patterns references/state-recovery.md '同一任务仅一份' '超过 20 轮' \
  '先保存并核对成功' '保存后再提问' '长计划开始执行前' \
  '步骤全部打勾不等于目标达成' '结果未知先核查' '终端断开不代表进程停止' \
  '不盲目重试' '不重置|次数继续有效' '不保存凭据或秘密' '本轮记录“正文待交付、状态待同步”'
check_patterns references/templates.md '用户原话或消息来源' '实际确认或委托的内容' '恢复后第一步' \
  '当前事项及未答部分' '产物版本' '第七步|独立复核要求'
check_patterns references/scenarios.md '多轮正反例' '环境恢复' '创作设计' '测试方案' \
  '执行中澄清后继续' '未知不等于取消'
check_patterns README.md '## 30 秒选择器' '## 文档导航' '历史整体复测尚未全部通过'
forbid_match '只请用户决定关键缺口|关键事项闭合后停止挖问题|不要求穷尽全部潜在问题' SKILL.md references/*.md
forbid_match 'SpecPacket|PlanPacket|TaskResult|ReviewReport|VerificationReport|GoalDraft' SKILL.md references/*.md
forbid_match '补齐正文后立即结束本轮|禁止展开后续需求清单' SKILL.md references/*.md

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
