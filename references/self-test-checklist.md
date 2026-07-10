# Self-Test Checklist

发布前或完成协议修改后运行以下检查。任一失败都必须回到对应文档修复，不得仅在最终报告中解释。

## Commands

```bash
scripts/check-contracts.sh
git diff --check
```

## Self-Test Improve Loop

自检不是一次性命令。每次协议、packet、反例、示例或发布元数据修改后，必须记录：

| 字段 | 要求 |
|---|---|
| check_item | 检查项，例如路径契约、目标分母、功能级验证、反例覆盖、packet 字段、版本一致性 |
| finding | critical / important / minor / none |
| route | executing / plan-revision / brainstorming / blocked / pass |
| fix | 修复动作或无需修复原因 |
| recheck | 复验命令、样例或人工检查 |
| evidence_strength | strong / medium / weak / stale |

同一问题最多 2 轮。仍失败时，不得说可发布，必须进入 blocked、plan-revision 或 brainstorming。

## Manual Gates

- `PlanPacket` 只使用 `gate_mode` 和 `execution_mode`，不得恢复 `mode`。
- `VerificationReport` 必须回填 `gate_mode` 和 `execution_mode`。
- `quality_level` 的机器值只能是 `mvp` / `polished` / `production`。
- `medium` 证据最多支持 `partial`，不得标 `met`。
- 目标定义必须包含 scope_denominator 和 target_principles；出现“全部 / 完整 / 100% / 迁移 / 覆盖”时不得缺少目标分母。
- Plan 必须包含 Target Coverage Matrix 和 Decomposition Strategy；不得用 Phase 标题、文件列表或产物名替代任务拆解。
- Verification 必须包含 Target coverage 和功能级证据；文件存在、文本命中、diff 审查不得支撑 `met`。
- 验收前自检必须包含 Self-test improve loop 摘要，证明发现、修复和复验已经闭环。
- lite / standard / strict 三条 walkthrough 都必须包含 SpecPacket、PlanPacket、TaskResult、ReviewReport、VerificationReport。
- README、SKILL、packet-contract、quality-rubric 对同一契约不得出现不同枚举或不同状态判定。

## Release Gate

只有以下全部成立时，才能说协议修改可发布：

| Gate | Required evidence |
|---|---|
| Contract lint | `scripts/check-contracts.sh` exit 0 |
| Markdown whitespace | `git diff --check` exit 0 |
| Golden paths | 三条 walkthrough 均通过脚本字段检查 |
| Packet templates | `references/packet-templates.md` 包含 5 类 packet |
| Quick start | `references/quick-start.md` 能在 30 秒内判断是否使用 Task Driver |
| Target rigor | Target / Plan / Verification 均能追踪 scope_denominator |
| Functional evidence | 完成声明由功能级验证或明确证据强度上限支撑 |
| Improve loop | 自检发现、修复、复验记录完整 |
