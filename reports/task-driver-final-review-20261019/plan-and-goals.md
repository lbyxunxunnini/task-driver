# 实际计划与验收目标原文

从实际父会话提取，保留原文中的判断与限制，不作正确性背书。原始记录第 69 行。

**当前环节：计划讨论（计划与验收目标合并展示）**

你已选择结束讨论，下面是计划草案和验收目标草案，一并请你确认。

---

## 计划事项 1：`Duration.mmss` 回归测试

### 已确认
为 `lib/common/utils/extension_duration.dart:3` 的 `mmss` 补回归测试；以现有行为为基线，覆盖常见输入、零值与边界；疑似缺陷按现有输出断言、单独分组注明非契约；不改该源文件。

### 实施方案
新增 `test/common/utils/extension_duration_test.dart`，纯 Dart 单测（`package:flutter_test` + `package:facesong_flutter/common/utils/extension_duration.dart`），标题沿用现有测试的英文风格。分三组：

- 常规：`Duration.zero` → `00:00`；5 秒 → `00:05`；59 秒 → `00:59`；60 秒 → `01:00`；61 秒 → `01:01`；59 分 59 秒 → `59:59`；1 小时 → `60:00`；100 分钟 → `100:00`（锁住"分钟不封顶"）。
- 边界：59999 毫秒 → `00:59`、1500 毫秒 → `00:01`（秒截断不四舍五入）；个位数分钟/秒的补零位数。
- 非契约组 `mmss - negative duration (non-contract)`：`Duration(seconds: -5)` → `00:55`、`Duration(seconds: -65)` → `-1:55`；组内注释写明这是记录现有输出、不是契约，将来修负时长必须同步改这一组。**这两个期望值是按 Dart `%` 语义推导的，未实测**，最终以统一跑测试的实际结果校准（只改测试文件内的期望值）。

### 涉及位置
仅新增 `test/common/utils/extension_duration_test.dart`。

## 计划事项 2：`Iterable.joinWith` 回归测试

### 已确认
为 `lib/common/utils/extension_list.dart:2` 的 `joinWith` 补回归测试；覆盖常见输入、空集合与边界；不改源文件。

### 实施方案
新增 `test/common/utils/extension_list_test.dart`（与源文件一一对应，两个扩展共用一个文件），按 `group('joinWith')` 分组：

- 常规：3 个元素 → 元素间插分隔符、首尾不加；分隔符值等于元素值时仍按位置插入。
- 空集合：`<int>[]` → 空列表；单元素 → 原样返回，不加分隔符。
- 边界：入参为 `Set` / 惰性 `Iterable.generate` 等非 `List` 可迭代对象；返回类型确为 `List<T>`（可 `.length`、可继续链式调用）；分隔符实例被复用而非复制（用 `identical` 断言，对应生产里传 Widget 实例的用法）。
- 我未在该扩展上发现疑似缺陷行为，因此**不设非契约组**（不为了凑格式编造）。

### 涉及位置
新增 `test/common/utils/extension_list_test.dart` 中的 `joinWith` 分组。

## 计划事项 3：`Iterable.excludeIndex` 回归测试

### 已确认
为 `lib/common/utils/extension_list.dart:5` 的 `excludeIndex` 补回归测试；覆盖常见输入、空集合与边界；不改源文件。

### 实施方案
同一文件内按 `group('excludeIndex')` 分组：

- 常规：剔除首位/中间/末位下标；值重复时只剔除该位置那一个（`[1,1,2].excludeIndex(0)` → `[1,2]`）；结果需 `.toList()` 后断言。
- 空集合：空输入 → 空结果。
- 边界：下标为负 → 原样返回全部；下标等于长度或远大于长度 → 原样返回全部；结果类型是惰性 `Iterable`（非 `List`）；同一个结果可重复遍历（`sync*` 可重入）。
- 判断说明：负下标/越界"静默返回全部"我判断为合理的防御行为，**不列入疑似缺陷**，放在边界组并加一行注释。若你认为它该进非契约组，计划确认时告诉我即可。

### 涉及位置
新增 `test/common/utils/extension_list_test.dart` 中的 `excludeIndex` 分组。

## 统一实施工作（非新增需求）

- **执行方式（并行）**：两个新文件目标与边界明确、可独立开始、互不引用对方产出、不同时改同一内容；测试按你的要求全部由主线程最后统一运行，子代理不跑测试，不争用 Flutter/构建缓存 → 并发条件成立。拟派两个执行子代理：A 只写 `extension_duration_test.dart`，B 只写 `extension_list_test.dart`；主线程不写测试文件，只负责整合、跑测试和自检。若你更想串行，产物完全相同，只是慢一些。
- **测试运行**：主线程执行一次 `fvm flutter test --no-pub --no-test-assets test/common/utils/extension_duration_test.dart test/common/utils/extension_list_test.dart`，只跑新增文件。
- **不触碰**：`lib/` 下任何文件、`pubspec.yaml`/`pubspec.lock`、`test/` 下已有 12 个文件；无任何 git 操作。
- **轻量计划摘要**：本任务跨"执行 → 独立审查 → 等你补标题 → 复核"多轮，中途会等你输入，我打算在执行开始时维护一份 `.task-driver/` 下的计划摘要防止上下文丢失（仅这一份，不含业务内容）。你不想要的话现在说，我就不写。
- **后续节奏（先说清）**：首次独立审查通过后，我把结果给你并停下等你补测试标题；收到标题后改标题，按规则仍需自检 + 独立子代理复核改动，复核通过才交付。所以"等你补标题"之后还有一轮复核。

---

## 验收目标草案

1. `Duration.mmss` 的回归测试已新增并通过，覆盖常规时长、零值、分钟不封顶与亚秒截断等边界；负时长按现有输出断言且单独分组注明非契约。
2. `Iterable.joinWith` 的回归测试已新增并通过，覆盖常规拼接、空集合、单元素、非 List 可迭代与分隔符实例复用。
3. `Iterable.excludeIndex` 的回归测试已新增并通过，覆盖常规剔除、空集合、负数与越界下标、惰性 Iterable 边界。
4. 改动只限当前副本新增的两个测试文件：`lib/` 全部文件、`pubspec.yaml`/`pubspec.lock`、`test/` 下已有 12 个文件内容未变（副本无 git，靠修改时间与内容抽查核对，无法做 diff）。

第 4 条是"只新增对应测试"的直接结果，属于你明确给定的边界，因此列为验收目标；第 1–3 条的通过证据是主线程统一跑新增测试的实际输出。

选择执行将同时确认以上计划、验收目标、执行范围和子代理设置。
