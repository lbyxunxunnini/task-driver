#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf 'check-ledger-loop: %s\n' "$1" >&2
  exit 1
}

usage() {
  cat <<'USAGE'
Usage: scripts/check-ledger-loop.sh <ledger-file>

Checks that a Task Driver ledger contains the minimum loop audit surface:
Target, packet records, Iteration Log, target coverage, self-test improve loop,
and no obvious weak-evidence completion claims.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

ledger="${1:-}"
[[ -n "$ledger" ]] || fail "missing ledger file argument"
[[ -f "$ledger" ]] || fail "ledger file not found: $ledger"

require_match() {
  local pattern="$1"
  local description="$2"
  rg -q "$pattern" "$ledger" || fail "missing ${description}: ${pattern}"
}

forbid_match() {
  local pattern="$1"
  local description="$2"
  if rg -n "$pattern" "$ledger" >/tmp/task-driver-ledger-hit.$$; then
    cat /tmp/task-driver-ledger-hit.$$ >&2
    rm -f /tmp/task-driver-ledger-hit.$$
    fail "forbidden ${description}: ${pattern}"
  fi
  rm -f /tmp/task-driver-ledger-hit.$$
}

require_match 'target_id|## Target|target:' 'Target anchor'
require_match 'spec_packet|SpecPacket' 'SpecPacket record'
require_match 'goal_draft|GoalDraft' 'GoalDraft record'
require_match 'plan_packet|PlanPacket' 'PlanPacket record'
require_match 'task_result|TaskResult' 'TaskResult record'
require_match 'review_report|ReviewReport' 'ReviewReport record'
require_match 'verification_report|VerificationReport' 'VerificationReport record'
require_match 'Iteration Log|attempt[[:space:]]*:|requirement_id' 'Iteration Log'
require_match 'target_coverage|Target coverage' 'target coverage'
require_match 'self_test_improve_loop|Self-test improve loop' 'self-test improve loop'
require_match 'isolated_goal_detection|isolated_goal_verifier' 'isolated goal detection'
require_match 'evidence_strength|strength[[:space:]]*:' 'evidence strength records'

forbid_match 'evidence_strength[[:space:]]*:[[:space:]]*(weak|stale).*status[[:space:]]*:[[:space:]]*met|strength[[:space:]]*:[[:space:]]*(weak|stale).*status[[:space:]]*:[[:space:]]*met' 'weak or stale evidence marked met'

python3 - "$ledger" <<'PY'
import re
import sys
from collections import Counter

path = sys.argv[1]
text = open(path, encoding="utf-8").read()

attempts = re.findall(r"requirement_id\s*:\s*([A-Za-z0-9_-]+)", text)
counts = Counter(attempts)
over_limit = sorted((req, count) for req, count in counts.items() if count > 2)
if over_limit:
    joined = ", ".join(f"{req}={count}" for req, count in over_limit)
    raise SystemExit(f"check-ledger-loop: requirement exceeds 2 loop attempts: {joined}")
PY

printf 'check-ledger-loop: ok\n'
