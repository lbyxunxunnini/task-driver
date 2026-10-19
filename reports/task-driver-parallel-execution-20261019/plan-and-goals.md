# 实际计划与验收目标原文

原始记录第 83 行。

**当前环节：输出计划（含验收目标草案）**

## 计划事项 1：Duration.mmss 时长格式化回归测试

### 已确认
- 以现有实现为基线，覆盖常见输入与边界；时长没有「空集合」，空集合只适用于计划事项 2
- 疑似缺陷场景（负数时长）全量锁定，单独分组并注明非契约
- 只新增测试，不改 `lib/common/utils/extension_duration.dart`

### 实施方案
新建 `test/common/utils/extension_duration_test.dart`，`import 'package:flutter_test/flutter_test.dart';` 与 `import 'package:facesong_flutter/common/utils/extension_duration.dart';`，按四个 group 组织：

1. **常规格式化**：0s→`"00:00"`、5s→`"00:05"`、59s→`"00:59"`、60s→`"01:00"`、61s→`"01:01"`、599s→`"09:59"`、3599s→`"59:59"`，分钟与秒两侧都覆盖到补零和不补零
2. **边界**：3600s→`"60:00"`（不做小时进位）、6000s→`"100:00"`（超两位不裁剪）、999ms→`"00:00"`、1500ms→`"00:01"`、1999ms→`"00:01"`（亚秒向零截断）
3. **当前实现的疑似缺陷行为（非约定契约）**：`Duration(seconds: -5)`、`Duration(seconds: -65)` 的实际输出

第 3 组按语言规则推导的结果是 `"00:55"` 和 `"-1:55"`（`inMinutes` 向零截断得 -1，`-65 % 60` 按 Dart 的欧几里得取模得 55，`"-1"` 已满两位不再补零）——**这是推导，未实际运行验证**。执行时先写断言再跑一次，若与实际输出不符，以实际输出为准修正断言，不修改业务源码。

### 涉及位置
新增 `test/common/utils/extension_duration_test.dart`；只读参考 `lib/common/utils/extension_duration.dart`。

### 内部验证
`fvm flutter test --no-pub --no-test-assets test/common/utils/extension_duration_test.dart`，最终并入统一运行。

## 计划事项 2：joinWith、excludeIndex 回归测试

### 已确认
- 覆盖常见输入、空集合和边界
- 疑似缺陷场景（越界与负数下标静默返回全部）全量锁定，单独分组并注明非契约
- 只新增测试，不改 `lib/common/utils/extension_list.dart`

### 实施方案
新建 `test/common/utils/extension_list_test.dart`，按六个 group 组织：

1. **joinWith 常规**：`[1,2,3].joinWith(0)`→`[1,0,2,0,3]`、`['a','b'].joinWith('-')`→`['a','-','b']`、单元素 `[1].joinWith(0)`→`[1]`（末尾分隔符被去掉）
2. **joinWith 空集合**：`<int>[].joinWith(0)`→`[]`、空 `Set` 同样为 `[]`
3. **joinWith 边界与契约**：返回新 `List` 且原集合内容与长度不变；分隔符与元素等值时 `[1,1].joinWith(1)`→`[1,1,1]`
4. **excludeIndex 常规**：`[1,2,3]` 分别去掉 0/1/2 号位得 `[2,3]`/`[1,3]`/`[1,2]`；空集合与单元素去掉 0 号位得 `[]`
5. **excludeIndex 边界**：对 `Iterable.generate` 无限序列 `.excludeIndex(0).take(3)` 可正常求值，锁定惰性；在 `Set` 上调用两个方法可用，锁定扩展作用于 `Iterable` 而非仅 `List`
6. **当前实现的疑似缺陷行为（非约定契约）**：`excludeIndex(3)`、`excludeIndex(99)`、`excludeIndex(-1)` 均原样返回全部元素且不抛异常

第 6 组同样以实际运行输出为准核对断言。

### 涉及位置
新增 `test/common/utils/extension_list_test.dart`；只读参考 `lib/common/utils/extension_list.dart`。

### 内部验证
`fvm flutter test --no-pub --no-test-assets test/common/utils/extension_list_test.dart`，最终并入统一运行。

## 统一实施工作（不计入需求事项）

- **执行方式**：两个测试文件互不引用、不共享辅助代码、不触碰同一文件，满足并发前提，因此由两个执行子代理分别只写各自文件，主线程整合。需要说明的是并行编写对两个小文件的提速有限，真正的约束是测试运行必须收口成一次。
- **测试运行**：按你的要求最后统一串行执行一次 `fvm flutter test --no-pub --no-test-assets test/common/utils/extension_duration_test.dart test/common/utils/extension_list_test.dart`，不并发起多个测试进程。
- **不改动**：业务源码、`pubspec.yaml`、已有测试文件均不改；不初始化 git、不提交推送。
- **未改动核实**：副本没有 `.git`，无法出 diff；改用文件时间戳核实 `lib/`、`pubspec.yaml` 与已有测试文件未被写入。

## 最终验收目标（草案）

1. 新增的两个回归测试文件在 `fvm flutter test --no-pub --no-test-assets` 的一次运行中全部通过，且覆盖已确认的正常输入、空集合、边界，以及单独分组标注的疑似缺陷场景。
2. `lib/` 下业务源码、`pubspec.yaml` 依赖声明与 `test/` 下已有测试文件保持未改动。
