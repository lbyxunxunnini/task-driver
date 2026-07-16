# 任务驱动项目规则

## 项目信息

- **名称**：任务驱动
- **版本**：v0.9.1
- **定位**：低认知负担的复杂任务推进 skill
- **GitHub**：[lbyxunxunnini/task-driver](https://github.com/lbyxunxunnini/task-driver)
- **父级规则**：[agent设计/CLAUDE.md](../CLAUDE.md)

## 当前核心链路

```text
仔细询问
-> 生成计划
-> 讨论计划
-> 生成验收标准
-> 讨论验收标准
-> 创建目标并执行
-> 自检未过则打回修复，最多 3 次
-> 无法修复则给出结论
```

## 关键文件

| 文件 | 职责 |
|------|------|
| `SKILL.md` | 触发规则和当前核心链路 |
| `README.md` | 面向安装和使用的说明 |
| `references/quick-start.md` | 极简使用示例 |
| `scripts/check-contracts.sh` | 防止旧流程和旧术语回退 |
| `VERSION.md` | 当前版本号 |
| `CHANGELOG.md` | 版本日志 |

## 开发规则

- 用户可见流程必须使用中文自然语言。
- 不再恢复旧的重流程和中间记录体系。
- 不再默认写中间文档；只有用户明确要求时才写。
- 验收标准必须单独生成、单独讨论、单独确认。
- 工程测试只能作为辅助检查，不能替代最终验收标准。
- 最终验收标准确认后必须创建目标或维护轻量目标。
- 未达成验收标准必须打回修复，全部达成后才能完成目标。
- 大任务写入必须先骨架后分块，避免一次性写入过大内容。
- 一个项目的一个任务最多只维护一份 `.task-driver/{任务标题}-{时间戳}-计划摘要.md`。
- 大任务、超大任务或长执行由模型自主判断必须写摘要；普通任务默认不写。
- 不得默认新建分支、提交、推送或合并。
- 修改协议后必须运行 `scripts/check-contracts.sh` 和 `git diff --check`。

## 版本管理

- 版本号同步：`SKILL.md` / `VERSION.md` / `.skillhub.json` / `README.md` / `CHANGELOG.md`。
- 版本对齐基准：本地 `VERSION.md` 文件。
- 发布前运行 `bash scripts/release_checks/metadata.sh`。

## Git 约束

- 提交信息前缀：`feat:` / `fix:` / `docs:` / `refactor:`
- 独立推送到 GitHub，不与其他子项目共享 git 历史。
