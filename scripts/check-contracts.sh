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

for file in SKILL.md README.md VERSION.md .skillhub.json \
  references/quick-start.md references/faq.md references/scenarios.md references/templates.md; do
  require_file "$file"
done
for name in explicit-discussion-request discussion-transition plan-with-implementation \
  acceptance-goal-discussion end-to-end-small-case user-acceptance-handoff task-splitting \
  exception-routing retry-strategy-change unified-exception-notice progressive-doc-routing \
  deferred-goal-tools visible-reply-boundary research-and-questioning review-authority-summary; do
  require_file "tests/dialogue-contracts/$name.md"
done

# 阶段、分支与公共门槛。只匹配短约束，不锁定整段写法。
check_patterns SKILL.md \
  '^## 协议结构' '^## 固定链路' \
  '^## 第一步：调查分析并逐项讨论' '^## 第二步：输出计划' \
  '^## 第三步：讨论并确认计划' '^## 第四步：输出并确认验收目标' \
  '^## 第五步：创建目标并执行' '^## 第六步：审查与修复闭环' \
  '^## 第七步：独立复核要求' '^## 第八步：' \
  '^### 完成判定与复审' '^### 异常分类' '^### 用户验收补位' \
  '可修复问题.*重新审查' '选择执行.*直接创建目标并执行' \
  '首审.*必要验收.*正文交付.*先完成'

check_patterns SKILL.md \
  '确认与授权' '仅要求推荐不属于委托决定' \
  '未反对.*回答其他事项.*模型汇总' '最终验收目标未确认前不得执行' \
  '用户实际肯定回答.*只确认其明确对象和范围' '模型建议或推荐.*仍为待确认' \
  '新建分支、提交、推送、合并、删除或发布.*必须另有明确授权' \
  '工程测试只是辅助证据，不能代替最终验收目标' \
  '已有执行授权.*必须复用' '项目外宿主记忆' '实际收费动作' \
  '每轮最多处理一个' '无须提问不代表讨论完成' \
  '不能只登记用户点名事项' '局部回答扩大为整体确认' \
  '模型不能自行结束讨论' '不增加确认汇总轮次' \
  '开始需求调研前.*必须读取' '明确需求不得重开为选项' \
  '未确认推荐不得算作已闭合' '未经确认或委托不得进入计划' \
  '不得因字段空白.*追问一般细节' '不设置固定问答轮数' \
  '逐项对照事实原始证据、用户回答对象及委托范围' \
  '不得先承认选项未知，后又承诺' '首次夹带重要新方案' \
  '用户选择生成计划后必须实际输出计划' \
  '尚需讨论时，首轮不得输出完整计划、验收目标或实施代码' \
  '不因“确认、1、继续”重新初始化' \
  '范围完整的工具总数' '不得声称精确总数或全部覆盖'

check_patterns SKILL.md \
  '正常对话正文交付' '同步选择器' '异步选择器' \
  'reasoning、工具说明/参数、内部状态、折叠过程消息和选择器不能替代正文' \
  '不得臆测界面已经验证' '未获回答时用最终正文和编号选项等待' \
  '已获回答时补齐正文并按原范围承接，不重问' \
  '补齐正文后立即结束本轮' '不重复文字提问' '原生选择器' \
  '开放了解事实' '核对理解' '原生自由输入' \
  '最终正文编号选项' '推荐.*超时或无回答.*不算执行授权'

check_patterns SKILL.md \
  '### 已确认' '### 实施方案' '核心机制.*作用边界.*关键约束' \
  '顶层按已确认的独立需求或问题组织' '合并或拆分必须说明来源和原因' \
  '预期变化、涉及位置、内部验证按需补充' '不另计需求或问题' \
  '统一实施工作' '任一不满足，禁止合并' \
  '同一回复.*统一执行选项' '执行，开启子代理' '执行，不开启子代理' \
  '不执行，继续讨论' '不增第四个业务选项' \
  '必须根据当前任务标注一个推荐、理由及各项影响' \
  '记录已确认计划，直接输出并讨论验收目标' \
  '用户选择生成后再输出完整目标草案' '不强制表格或条数' \
  '原样跟踪，不增工程目标、不改粒度或解释' \
  '删除判断' '不得.*施工步骤.*反推' '禁止按文件、模块、测试场景或实施步骤拆目标'

check_patterns SKILL.md \
  '实际工具和 schema' 'select:TaskCreate' 'select:TaskList' 'select:TaskUpdate' \
  'Invalid tool parameters' '重试一次' '必须先查询已有任务' '禁止重复创建' \
  '保存返回 ID' '原样跟踪目标.*保留无关条目' '两类工具均不可用才在对话中跟踪' \
  '展示草案不等于创建目标' '实际工作前.*首次文档骨架' \
  '用 `TaskUpdate` 或实际计划工具先更新执行中' \
  '按真实结果映射 `TaskUpdate` 或计划工具状态' \
  '聚合目标完整承载已确认目标.*每条目标只对应一条任务' \
  '先恢复执行中' '复核整项目标' '超过 200 行' \
  '未达成、受阻' '不得伪记完成'

check_patterns SKILL.md \
  '无论是否开启子代理.*主模型.*必须' '主模型审查实际交付' \
  '不得因关闭子代理、产物已生成或需要主观验收就跳过检查' \
  '判断必须对应原目标、实际交付和证据' '不得新增标准或超出检查范围' \
  '质量判断只分两档' '\| 达标 \|' '\| 未达标 \|' \
  '\| 可修复 \|' '\| 需要用户验收 \|' '\| 需要用户授权或决定 \|' '\| 受阻 \|' \
  '同一最终目标最多修复 3 次' '第三次修复后仍必须完成复验' \
  '改变策略或修复内容' '相同原因与处理方式反复失败' \
  '独立审查最多 3 次' '输入不合规后的重审均计入' \
  '目标.*保持未完成|保持未完成' '工具内生成或准备输出不算交付' \
  '需要用户验收.*不计修复次数' '需要用户授权或决定.*不计修复次数' \
  '\| 受阻 \|.*不计修复次数' \
  '无范围内已知缺陷或回归破坏' '等待不等于用户无法验收'
check_patterns SKILL.md '先交付结果，再更新完成' '下次自然续接时核对后补记' '不为补记额外索取用户确认'
check_patterns SKILL.md \
  '无法完成必要验收，且无其他可靠证据.*受阻' \
  '已开启独立复核.*已通过且覆盖当前交付版本' \
  '发出前必须读取并遵守\[统一异常通知骨架\]' \
  '通知前必须读取并遵守\[用户验收通知格式\]'

check_patterns SKILL.md \
  '首审和复审均使用独立上下文' '交接.*独立审查交接模板' \
  '禁止执行者自评和前次审查结论' '无法判断：审查输入不合规' \
  '保留原记录' '全新独立上下文重审' '不得删改原审查报告' \
  '输入检查和输出要求原文' '可访问协议位置' '不扩大核实权限' \
  '\| 状态 \|' '\| 证据 \|' '\| 阻断原因 \|' '\| 回归破坏 \|' \
  '不只采信汇总' '未受影响的有效证据可复用'
check_patterns SKILL.md '不静默关闭或声称已审查' '未达成、回归或无法判断均按第六步分类'

check_patterns SKILL.md \
  '条件独立触发' '超过 20 轮' '禁止写入时不得写' \
  '首次写前必须告知' '计划摘要.md' '单份|同一任务只维护' \
  '回滚关系' '不得静默拆分' '决定执行方式前.*必须读取' \
  '不按文件数、计划项数或目标数机械判断' \
  '提出拆分依据、建议首批范围和延期事项，请用户确认本轮范围' \
  '只读取当前任务所需资料，不要求每次全量加载' \
  '统一异常通知骨架' '用户验收通知格式' '高风险复核' \
  '没有必要验收要求时不得新增人工确认' '已有修复/审查次数' \
  '实际差异' '不得批量伪标完成'

# 引用资料各司其职；保留历史验证限制。
check_patterns README.md '## 30 秒选择器' '即使不采用' '不得伪造验收目标或越权' \
  '禁止要求用户再次确认已知限制' \
  '## 能力边界与环境适配' '## 文档导航' '历史整体复测尚未全部通过'
check_patterns references/quick-start.md 'README.md#30-秒选择器' '核心链路' '每一步怎么说' '典型反例'
check_patterns references/faq.md '## 问题索引' '## 原生选择器怎样使用' \
  '## 三次修复是必须执行三次吗' '## 用户验收和独立复核谁先' '第三次也必须复验'
check_patterns references/scenarios.md '## 调研与讨论方法' '无法联网时必须基于自身知识继续深入分析' \
  '先用自身知识分析场景和可行路径' '场景建议不能代替用户决定' \
  '以下条件全部满足时，必须拆分并发' '必须由主线程串行执行' \
  '## 低风险 Bug 修复' '## 新功能或新模块建设' '## 跨模块重构' \
  '## 生产配置、外部接口或费用任务' '## UI、设备体验或主观质量任务' \
  '禁止展开后续需求清单、技术选型或确认继续的选项'
check_patterns references/templates.md '必须明确通知“需要用户验收”' \
  '不得新增模型自造标准' '不粘贴长日志或内部状态转储' \
  '当前结果：' '原因：' '已完成：' '下一步：' \
  '第七步：独立复核要求'

# 契约描述行为与失败路径，不以它们的存在代替回放。
check_patterns tests/dialogue-contracts/retry-strategy-change.md '第三次修复' '第四次修复' '独立审查三次'
check_patterns tests/dialogue-contracts/review-authority-summary.md '独立首审的必要证据' \
  '无子代理的完整闭环' '输入不合规' '未受影响内容的审查证据可以复用'
check_patterns tests/dialogue-contracts/deferred-goal-tools.md '场景四' '工具输出' '正常正文' 'completed'
check_patterns tests/dialogue-contracts/deferred-goal-tools.md '本轮保留工具未完成' '不额外要求确认'
check_patterns tests/dialogue-contracts/progressive-doc-routing.md '不采用时仍不得伪造目标或越权' '静态|行为|复测|单一宿主'
check_patterns tests/dialogue-contracts/user-acceptance-handoff.md '编号操作步骤' '预期结果和通过条件'
check_patterns tests/dialogue-contracts/visible-reply-boundary.md '原生选择器不能替代正文' '异步' '同步'
check_patterns tests/dialogue-contracts/deferred-goal-tools.md \
  '实施步骤不创建为宿主任务' '工作完成后只更新内部状态，不调用 `TaskUpdate`' \
  '首次写入文档骨架后才把对应任务更新为执行中' '中断恢复或调用失败后重复创建相同任务'
check_patterns tests/dialogue-contracts/exception-routing.md \
  '影响目标达成的必要条件尚未核实' '后三类异常不消耗最多 3 次的修复次数'
check_patterns tests/dialogue-contracts/discussion-transition.md '写歌会话对照回放'
check_patterns tests/dialogue-contracts/task-splitting.md '模型只请用户确认本轮范围'
check_patterns tests/dialogue-contracts/end-to-end-small-case.md \
  '五项目标覆盖' '模型一次只讨论一个问题' '提供继续讨论或生成计划的选择' \
  '每项展示已确认决策和实施方案' '输出两个最终验收目标草案，并提供三个执行选项' \
  '选择执行后原样创建已展示的目标并执行'
check_patterns tests/dialogue-contracts/unified-exception-notice.md \
  '编号验收步骤和每步预期结果' '明确通过条件和反馈要求'

set -- SKILL.md README.md references/quick-start.md references/faq.md references/scenarios.md references/templates.md
forbid_match 'SpecPacket|PlanPacket|TaskResult|ReviewReport|VerificationReport|GoalDraft' "$@"
forbid_match 'gate_mode|execution_mode|brainstorming|planning|executing|verification' "$@"
forbid_match '\.task-driver/(specs|plans|ledgers)|必须使用轻量表格' "$@"
forbid_match '计划确认只代表“可以进入验收标准草案”|够用|有瑕疵|不够用' "$@"
forbid_match 'approved spec|approved plan|Acceptance Criteria|Target Coverage Matrix|Decomposition Strategy|File Map' "$@"
forbid_match '拿不准的目标.*不阻塞|草案末尾提供两个选择|最终确认前，先询问是否开启' "$@"
forbid_match '仔细询问[[:space:]]*$' README.md references/quick-start.md
forbid_match '^## 30 秒选择器|发出回复后立即结束本轮|最终文本或宿主实际展示的原生提问' SKILL.md

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
