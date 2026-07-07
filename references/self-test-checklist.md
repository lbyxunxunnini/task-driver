# Self-Test Checklist

发布前或完成协议修改后运行以下检查。任一失败都必须回到对应文档修复，不得仅在最终报告中解释。

## Commands

```bash
scripts/check-contracts.sh
git diff --check
```

## Manual Gates

- `PlanPacket` 只使用 `gate_mode` 和 `execution_mode`，不得恢复 `mode`。
- `VerificationReport` 必须回填 `gate_mode` 和 `execution_mode`。
- `quality_level` 的机器值只能是 `mvp` / `polished` / `production`。
- `medium` 证据最多支持 `partial`，不得标 `met`。
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
