# Resume Protocol

断点续传与自动恢复协议。当任务中断后重新触发时，agent 必须按本协议判定是否可从断点续传，避免重复工作。

## Checkpoint 格式

每个 TaskResult 写入 ledger 后，必须在 ledger 末尾追加 `## Resume Checkpoint` 段：

```yaml
resume_checkpoint:
  last_completed_task: "T-003"
  next_task: "T-004"
  phase: executing
  git_sha: "abc1234"
  files_snapshot:
    - path: src/foo.ts
      sha: "def5678"
    - path: src/bar.ts
      sha: "ghi9012"
  completed_ac_ids: ["AC-1", "AC-2"]
  iteration_count:
    "AC-1": 1
  updated_at: "YYYY-MM-DD HH:MM:SS"
```

## 恢复判定

进入 executing 阶段时，先检查 ledger 是否存在且末尾有 `## Resume Checkpoint`：

1. 读取 `git_sha`：若与当前 HEAD 一致，且 `files_snapshot` 中各文件 SHA 未变化 → **可续传**。
2. 若 git_sha 不一致或文件有变化 → **不可续传**，从 T-001 重新开始，在 ledger 记录 `resume: skipped (state changed)`。
3. 若可续传 → 从 `next_task` 继续，在 ledger 记录 `resume: continued from T-NNN`，跳过所有 `last_completed_task` 之前的任务。

Plan 阶段和 verification 阶段同理：phase 字段标识当前阶段，恢复时直接进入该阶段。

## 自动重试白名单

以下错误类型为可恢复错误，agent 必须自动重试 1 次，而非立即停机：

| 错误类型 | 判定条件 | 重试策略 |
|---|---|---|
| `lint-fix` | linter 报告可自动修复的问题 | 自动应用 lint fix，重新验证 |
| `test-flaky` | 测试失败但错误信息包含 timeout / race / connection refused | 等待 2s 后重跑同一命令 |
| `file-lock` | 文件被其他进程占用 | 等待 1s 后重试操作 |
| `network-retry` | 包管理器的网络超时（npm install / pip / cargo 等） | 重试 1 次同一命令 |

重试规则：
- 每种错误只自动重试 **1 次**。
- 重试后仍失败 → 升级为停机回问，使用对应错误模板。
- 重试必须在 ledger 的 `## Iteration Log` 中记录 attempt = `auto-retry`。
- 安全、权限、数据、发布相关操作**不适用**自动重试，必须直接停机。

## 预检门禁

进入每个阶段前，执行预检。预检失败不得进入该阶段。

### Executing 预检

- [ ] git status 干净（或无冲突文件）
- [ ] spec 文件存在且状态为 Approved
- [ ] plan 文件存在且状态为 Approved
- [ ] ledger 文件存在
- [ ] 当前分支符合 plan 要求

### Verification 预检

- [ ] 所有 PlanPacket.tasks[] 都有 TaskResult
- [ ] 所有 TaskResult 都有 ReviewReport（或已记录豁免原因）
- [ ] 无未关闭的 Critical / Important finding
- [ ] ledger 中 `## Iteration Log` 无超过 2 轮的 requirement

预检失败时，输出具体失败项和建议动作（回到 executing / plan-revision / blocked），不得跳过进入下一阶段。

## 与错误模板的协作

自动重试白名单是错误模板的前置处理层：

1. 错误发生 → 匹配白名单 → 匹配成功 → 自动重试 1 次 → 成功则继续，失败则升级
2. 错误发生 → 匹配白名单 → 不匹配 → 直接使用对应错误模板（停机回问 / 验证失败 / 循环退出 / 范围漂移 / 阻塞状态）
3. 安全/权限/数据/发布相关错误 → 跳过白名单匹配，直接停机
