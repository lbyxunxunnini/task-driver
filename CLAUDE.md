# Task Driver — 项目规则

## 项目信息

- **名称**：task-driver
- **版本**：v0.8.4
- **定位**：重任务总控：需求澄清→计划→执行→验证，分阶段推进
- **GitHub**：[lbyxunxunnini/task-driver](https://github.com/lbyxunxunnini/task-driver)
- **父级规则**：[agent设计/CLAUDE.md](../CLAUDE.md)

## 关键文件

| 文件 | 职责 |
|------|------|
| `SKILL.md` | 触发规则、阶段定义、协议引用 |
| `references/` | 协议、glossary、模板、反例 |
| `VERSION` | 当前版本号 |
| `CHANGELOG.md` | 版本日志 |

## 开发规则

- 所有阶段输出使用中文，机器契约字段保持英文
- 反例和防错规则放在 `references/` 下，不内联到 SKILL.md
- glossary 是必读文件，首次用户在使用阶段/协议/状态名前必须先读
- 阶段间的交接必须有结构化数据（spec / plan / ledger），不得用自然语言传递

## 版本管理

- 5 处版本号同步：`SKILL.md` / `VERSION` / `.skillhub.json` / `README.md` / `CHANGELOG.md`
- 版本对齐基准：本地 `VERSION` 文件
- 发布前运行 `bash scripts/release_checks/metadata.sh`（如有）
- 详细发布流程见 [docs/skill-publishing.md](../docs/skill-publishing.md)

## Git 约束

- 提交信息前缀：`feat:` / `fix:` / `docs:` / `refactor:`
- 独立推送到 GitHub，不与其他子项目共享 git 历史
