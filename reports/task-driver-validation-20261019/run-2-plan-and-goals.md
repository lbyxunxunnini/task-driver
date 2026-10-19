# 真实会话产物：计划与验收目标草案

以下保留原始输出，未由主代理改写。方案产出不代表目标已确认或执行。

已完成只读排查，关键事实已确认：

- 真正的设置页是 `lib/screens/setting/setting_screen.dart`，从“我的 → 设置”进入（`me_controller.dart:137` → `PageConfigs.setting`）。
- 入口文案在 `setting_screen.dart:75`，点击跳转仍使用 `PageConfigs.settingFeedback`。
- 同一文案还出现在反馈页两处、以及应用内无导航入口的“隐私设置”页一处，这些都不属于本次“设置页入口”范围。

## 计划草案

**任务目标**：把设置页入口“建议与反馈”改为“意见反馈”，跳转目标和反馈页内容保持原样。

**计划依据**：已确认 1 个需求，对应 1 个计划事项。

### 1. 设置页入口文案更名

#### 已确认

- 只修改设置页入口显示文案：“建议与反馈” → “意见反馈”。
- 入口位置、`onTap` 行为和 `PageConfigs.settingFeedback` 跳转保持不变。
- 反馈页内的标题“建议与反馈”、正文小标题、输入提示、发送日志、提交按钮等内容全部不修改。
- 同文案在 `lib/screens/setting/privacy_setting.dart`（隐私设置页）也有一处，但该页面应用内没有导航入口，不属于本次“设置页入口”，不改动。

#### 预期变化

- 现状：设置页列表中显示“建议与反馈”。
- 实施后：同一位置显示“意见反馈”，点击仍进入原反馈页，反馈页内容与修改前一致。

#### 实施方案

- 修改 `lib/screens/setting/setting_screen.dart:75`：`title: '建议与反馈'.tr` → `title: '意见反馈'.tr`。
- 不修改 `PageConfigs.settingFeedback`、`lib/router/app_routes.dart`、`lib/screens/setting/setting_feedback_screen.dart`。
- 本地翻译文件 `lib/lang/zh_cn.dart` 中未找到该文案映射，`.tr` 会按 GetX 规则回退显示原字符串，因此不需要改翻译文件。
- 修改后用文本检索核对剩余“建议与反馈”只出现在反馈页和隐私设置页，范围符合预期。

#### 涉及位置

- `lib/screens/setting/setting_screen.dart`：仅入口文案一行。

#### 内部验证

- `git diff`：确认只有这一行文案变化，没有路由或页面改动。
- `fvm flutter analyze --no-pub`：确认静态分析通过。
- 若模拟器可用，启动应用走“我的 → 设置”确认文案和跳转；不可用时明确说明，并提交你做界面验收。

## 验收目标草案

1. 设置页中原“建议与反馈”入口显示为“意见反馈”，位置不变。
2. 点击该入口仍进入原反馈页，反馈页的标题、提示语、发送日志选项、提交按钮等内容与修改前一致。

选择执行将同时确认本轮展示的计划、最终验收目标、执行范围和子代理设置。
