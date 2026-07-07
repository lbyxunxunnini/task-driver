# Strict Walkthrough

场景：用户要求修改权限校验逻辑并准备发布，涉及安全、公共 API 和回滚风险。

## Trigger

```text
tdr- 修复管理员 API 权限绕过问题，要求生产级，包含回归测试和发布前验证
```

## Decision

- gate_mode: strict
- execution_mode: multi-agent-review
- 原因：涉及权限、安全、公共 API 和生产级质量。若当前环境没有 subagent，必须降级为 `single-agent` 并记录原因，但 gate_mode 仍保持 `strict`。

## Spec Summary

```yaml
spec_packet:
  spec_path: docs/task-driver/specs/2026-07-07--admin-api-authz.md
  goal: "修复管理员 API 权限绕过"
  target:
    target_id: admin-api-authz
    target_statement: "非管理员无法访问管理员 API，管理员正常路径不回归。"
    success_definition: "安全、权限、回归、发布前验证全部有 strong evidence；无 Critical/Important finding。"
    quality_level: production
    stop_or_loop_conditions: "权限模型或 API contract 变化回到 brainstorming；任务顺序或测试策略错误回到 planning；实现缺陷回到 executing。"
  decision_trace:
    - layer: 整体目标
      decision_point: "修复目标是拒绝非管理员还是重构权限系统?"
      options_summary: "最小安全修复 / 权限系统重构"
      decision: "最小安全修复"
      impact: "Scope 限定当前 API；重构进入 Non-Goals。"
    - layer: 风险分支
      decision_point: "是否允许发布前跳过集成测试?"
      options_summary: "允许 / 不允许"
      decision: "不允许"
      impact: "Verification Strategy 必须含权限集成测试。"
  grilling_summary:
    shared_understanding: true
    unresolved_branches: []
    key_tradeoffs: ["先封堵安全漏洞，不重构权限系统"]
    rejected_paths: ["扩大到全站 RBAC 重构", "跳过集成测试"]
  design_tree_coverage:
    - branch_id: B1
      name: authz failure mode
      parent: root
      layer: 行为细节
      status: decided
      decision_ref: "Decision Trace: 整体目标"
      blocks: []
    - branch_id: B2
      name: release risk
      parent: B1
      layer: 实现约束
      status: decided
      decision_ref: "Decision Trace: 风险分支"
      blocks: []
  acceptance_criteria:
    - id: AC-1
      description: "非管理员访问管理员 API 返回 403"
      verification: "integration authz test"
    - id: AC-2
      description: "管理员访问管理员 API 仍成功"
      verification: "integration happy path test"
    - id: AC-3
      description: "公共 API contract 不变"
      verification: "contract test"
    - id: AC-4
      description: "发布前验证和回滚说明齐备"
      verification: "release checklist"
  constraints:
    - "不得扩大权限模型"
    - "不得跳过集成测试"
    - "必须记录回滚方案"
  quality_level: production
  approved_by_user: true
  status: approved
```

## Plan Summary

```yaml
plan_packet:
  plan_path: docs/task-driver/plans/2026-07-07--admin-api-authz.md
  ledger_path: docs/task-driver/ledgers/2026-07-07--admin-api-authz.md
  plan_version: v1
  predecessor: 无
  gate_mode: strict
  execution_mode: multi-agent-review
  tasks:
    - id: T-001
      owner_role: Implementer
      objective: "新增权限绕过失败测试"
      files: [tests/admin-authz.test.ts]
      verification: ["npm test -- admin-authz"]
      acceptance_ac_ids: [AC-1, AC-2]
    - id: T-002
      owner_role: Implementer
      objective: "修复管理员 API 权限判断"
      files: [src/routes/admin.ts, src/auth/permissions.ts]
      verification: ["npm test -- admin-authz", "npm test -- contract"]
      acceptance_ac_ids: [AC-1, AC-2, AC-3]
    - id: T-003
      owner_role: Verifier
      objective: "执行发布前验证和回滚检查"
      files: [docs/release/admin-authz.md]
      verification: ["npm test -- admin-authz", "npm test -- contract", "npm run build"]
      acceptance_ac_ids: [AC-4]
  stop_conditions:
    - "权限模型需要扩展"
    - "contract test 要求改变公共 API"
    - "任何安全测试无法运行"
  status: approved
```

## Review Gate

```yaml
task_result:
  task_id: T-003
  status: done
  files_changed:
    - src/routes/admin.ts
    - src/auth/permissions.ts
    - tests/admin-authz.test.ts
    - docs/release/admin-authz.md
  commands_run:
    - command: "npm test -- admin-authz"
      exit_code: 0
    - command: "npm test -- contract"
      exit_code: 0
    - command: "npm run build"
      exit_code: 0
  evidence:
    - id: EV-1
      command: "npm test -- admin-authz"
      result: "non-admin denied; admin allowed"
      strength: strong
      covers_requirement_ids: [AC-1, AC-2]
    - id: EV-2
      command: "npm test -- contract"
      result: "contract unchanged"
      strength: strong
      covers_requirement_ids: [AC-3]
    - id: EV-3
      command: "npm run build"
      result: "build passed; release checklist updated"
      strength: strong
      covers_requirement_ids: [AC-4]
  ac_coverage:
    - ac_id: AC-1
      covered: full
      evidence: [EV-1]
    - ac_id: AC-2
      covered: full
      evidence: [EV-1]
    - ac_id: AC-3
      covered: full
      evidence: [EV-2]
    - ac_id: AC-4
      covered: full
      evidence: [EV-3]
  deviations_from_plan: []

review_report:
  task_id: T-002
  status: pass
  findings: []
```

strict 模式下，Critical finding 不得 deferred；Important 只有在不影响 AC、安全、权限、数据、发布、依赖、构建配置或公共 API 时才可被用户明确 deferred。

## Verification

```yaml
verification_report:
  status: awaiting_user_acceptance
  gate_mode: strict
  execution_mode: multi-agent-review
  coverage:
    - ac_id: AC-1
      evidence_ref: EV-1
      evidence_strength: strong
      status: met
    - ac_id: AC-2
      evidence_ref: EV-1
      evidence_strength: strong
      status: met
    - ac_id: AC-3
      evidence_ref: EV-2
      evidence_strength: strong
      status: met
    - ac_id: AC-4
      evidence_ref: EV-3
      evidence_strength: strong
      status: met
  pre_acceptance_self_check:
    plan_tasks: pass
    review_reports: pass
    ac_coverage: pass
    verification_strategy: pass
    scope_drift: pass
    quality_gate: pass
    residual_risk: pass
  unmet_requirements: []
  delivery_acknowledged_by_user: pending
  quality_score:
    overall: 4.6
    threshold: 4.5
    decision: pass
    evidence_refs: [EV-1, EV-2, EV-3]
    rationale: "production 门槛下，安全、权限、contract、build 和回滚均有 strong evidence。"
```

要点：strict 模式的价值不是多写文档，而是拒绝在安全/权限/发布风险上用 partial 或 weak evidence 包装完成。
