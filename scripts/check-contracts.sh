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
  rg -q "$pattern" "$path" || fail "missing pattern in $path: $pattern"
}

forbid_match() {
  local pattern="$1"
  local scope="$2"
  if rg -n "$pattern" $scope >/tmp/task-driver-contract-hit.$$; then
    cat /tmp/task-driver-contract-hit.$$ >&2
    rm -f /tmp/task-driver-contract-hit.$$
    fail "forbidden pattern found: $pattern"
  fi
  rm -f /tmp/task-driver-contract-hit.$$
}

require_file SKILL.md
require_file README.md
require_file references/packet-contract.md
require_file references/quality-rubric.md
require_file references/packet-templates.md
require_file references/quick-start.md
require_file references/walkthroughs/lite.md
require_file references/walkthroughs/standard.md
require_file references/walkthroughs/strict.md
require_file scripts/check-ledger-loop.sh

DOC_SCOPE='SKILL.md README.md references'

forbid_match 'PlanPacket\.mode|写入 PlanPacket\.mode|medium 可标 Met|Quality level:\*\* 精打磨|quality_level: Polished|quality_level: \[MVP|docs/task-driver/|YYYY-MM-DD--slug' "$DOC_SCOPE"

require_match 'PlanPacket\.gate_mode' SKILL.md
require_match 'PlanPacket\.execution_mode' SKILL.md
require_match '\.task-driver/specs/YYYYMMDD-HHmm-主题\.md' SKILL.md
require_match 'gate_mode \| enum \| yes \| strict / standard / lite' references/packet-contract.md
require_match 'execution_mode \| enum \| yes \| single-agent / multi-agent-review / multi-agent-parallel / degraded-single-skill' references/packet-contract.md
require_match 'scope_denominator' references/packet-contract.md
require_match 'target_principles' references/packet-contract.md
require_match 'target_coverage_matrix' references/packet-contract.md
require_match 'decomposition_strategy' references/packet-contract.md
require_match 'target_coverage' references/packet-contract.md
require_match 'GoalDraft' references/packet-contract.md
require_match 'goal_provider.*codex / claude-code / ledger-only' references/packet-contract.md
require_match 'goal_detection' references/packet-contract.md
require_match 'fallback_policy' references/packet-contract.md
require_match 'isolated_goal_detection' references/packet-contract.md
require_match 'mvp / polished / production' references/packet-contract.md
require_match 'medium.*最多.*Partial' references/packet-contract.md
require_match 'weak.*文件存在、文本命中' references/packet-contract.md
require_match 'mvp.*threshold = 3' references/quality-rubric.md
require_match 'polished.*threshold = 4' references/quality-rubric.md
require_match 'production.*threshold = 4.5' references/quality-rubric.md

# 启动预检门 + 写入屏障 + 优先级声明（防协议被改回松散状态）
require_match '启动预检门' SKILL.md
require_match '写入屏障' SKILL.md
require_match '优先级声明' SKILL.md
require_match '先确认再执行.*优先于.*主动执行' SKILL.md
require_match 'apply_patch.*重定向写文件' SKILL.md
require_match 'mkdir.*创建目录.*\.task-driver' SKILL.md
require_match 'spec/plan 产出不受屏障约束' SKILL.md
require_match '小任务内联的时序规则' SKILL.md
require_match '读完协议后直接执行' references/counterexamples/global.md
require_match '口头计划替代已确认计划' references/counterexamples/global.md
require_match '预热创建工件目录' references/counterexamples/global.md
require_match '阶段交接裸贴机器契约' references/counterexamples/global.md
require_match '目标模式过早激活' references/counterexamples/global.md
require_match '静默覆盖已有 Goal' references/counterexamples/global.md
require_match '证据不足就完成 Goal' references/counterexamples/global.md
require_match '同上下文自证目标完成' references/counterexamples/global.md
require_match '评估结论展示模板' references/packet-templates.md
require_match 'GoalDraft 分组表格展示模板' references/packet-templates.md
require_match 'isolated_goal_verifier' references/packet-templates.md
require_match 'same-context self-check' references/packet-templates.md
require_match 'evaluation_result' references/packet-templates.md
require_match 'Goal Compatibility Lifecycle' references/runtime-protocols.md
require_match '隔离目标检测' references/runtime-protocols.md
require_match '不得降级为同上下文自检' references/runtime-protocols.md
require_match 'Claude Code.*evaluator.*只看对话' references/runtime-protocols.md
require_match 'Goal Complete Gate' references/modes/verification.md
require_match 'isolated_goal_detection.status 为 pass' references/modes/verification.md
require_match 'GoalDraft 必须从 approved SpecPacket.target 派生' references/modes/planning.md
require_match 'GoalDraft.goal_detection.required 是否为 true' references/modes/planning.md
require_match 'fallback_policy' references/modes/planning.md
require_match '读取 GoalDraft 并激活目标兼容层' references/modes/executing.md
require_match 'check-ledger-loop' scripts/check-ledger-loop.sh
require_match 'self_test_improve_loop|Self-test improve loop' scripts/check-ledger-loop.sh
require_match 'isolated_goal_detection|isolated_goal_verifier' scripts/check-ledger-loop.sh
require_match 'requirement exceeds 2 loop attempts' scripts/check-ledger-loop.sh
require_match '未确认 spec/plan 就创建工件目录或文件' references/counterexamples/executing.md

for template in SpecPacket PlanPacket GoalDraft TaskResult ReviewReport VerificationReport; do
  require_match "$template" references/packet-templates.md
done

for mode in lite standard strict; do
  require_match "gate_mode: $mode" "references/walkthroughs/$mode.md"
  require_match 'execution_mode:' "references/walkthroughs/$mode.md"
  require_match 'scope_denominator:' "references/walkthroughs/$mode.md"
  require_match 'target_principles:' "references/walkthroughs/$mode.md"
  require_match 'target_coverage_matrix:' "references/walkthroughs/$mode.md"
  require_match 'decomposition_strategy:' "references/walkthroughs/$mode.md"
  require_match 'target_coverage:' "references/walkthroughs/$mode.md"
  require_match 'spec_packet:' "references/walkthroughs/$mode.md"
  require_match 'goal_draft:' "references/walkthroughs/$mode.md"
  require_match 'goal_detection:' "references/walkthroughs/$mode.md"
  require_match 'fallback_policy:' "references/walkthroughs/$mode.md"
  require_match 'plan_packet:' "references/walkthroughs/$mode.md"
  require_match 'task_result:' "references/walkthroughs/$mode.md"
  require_match 'review_report:' "references/walkthroughs/$mode.md"
  require_match 'verification_report:' "references/walkthroughs/$mode.md"
  require_match 'isolated_goal_detection:' "references/walkthroughs/$mode.md"
done

printf 'check-contracts: ok\n'
