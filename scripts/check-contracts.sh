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
require_file VERSION

DOC_SCOPE='SKILL.md README.md CLAUDE.md references/quick-start.md'

require_match '仔细询问' SKILL.md
require_match '生成计划' SKILL.md
require_match '讨论计划' SKILL.md
require_match '生成验收标准' SKILL.md
require_match '讨论验收标准' SKILL.md
require_match '创建目标并执行' SKILL.md
require_match '最多 3 次' SKILL.md
require_match '无法修复则给出结论' SKILL.md
require_match '不默认新建分支' SKILL.md
require_match '不自动合并临时分支' SKILL.md
require_match '工程测试只能作为辅助检查' SKILL.md
require_match '最终验收标准' SKILL.md
require_match '目标内容只能来自最终验收标准' SKILL.md
require_match '打回修复' SKILL.md
require_match '大任务写入规则' SKILL.md
require_match '先问为什么做和做成什么样' SKILL.md
require_match '轻量计划摘要' SKILL.md
require_match '\.task-driver/\{任务标题\}-\{YYYYMMDDHHmmss\}-计划摘要\.md' SKILL.md
require_match '一个项目的一个任务，只允许维护一份计划摘要' SKILL.md
require_match '由模型自主判断' SKILL.md
require_match '序号 \| 要做什么 \| 范围 \| 状态' SKILL.md
require_match '序号 \| 验收标准 \| 检查方式 \| 状态' SKILL.md
require_match '草案、已确认、执行中、已完成、已取消' SKILL.md
require_match '草案、已确认、已达成、未达成、受阻' SKILL.md

require_match '仔细询问' README.md
require_match '讨论验收标准' README.md
require_match '权限边界' README.md
require_match 'v0.9.0' README.md
require_match '当前核心链路' CLAUDE.md
require_match '不再恢复旧的重流程' CLAUDE.md
require_match '固定链路' references/quick-start.md
require_match '禁止事项' references/quick-start.md
require_match '大任务写入' references/quick-start.md
require_match '自检打回' references/quick-start.md
require_match '轻量计划摘要' references/quick-start.md

forbid_match 'SpecPacket|PlanPacket|TaskResult|ReviewReport|VerificationReport|GoalDraft' "$DOC_SCOPE"
forbid_match 'gate_mode|execution_mode|brainstorming|planning|executing|verification' "$DOC_SCOPE"
forbid_match 'approved spec|approved plan|Acceptance Criteria|Target Coverage Matrix|Decomposition Strategy|File Map' "$DOC_SCOPE"
forbid_match '\.task-driver/(specs|plans|ledgers)' "$DOC_SCOPE"

printf 'check-contracts: ok\n'
