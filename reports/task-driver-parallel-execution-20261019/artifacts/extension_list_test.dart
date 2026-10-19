import 'package:facesong_flutter/common/utils/extension_list.dart';
import 'package:flutter_test/flutter_test.dart';

/// 无限自然数序列，用于验证 excludeIndex 的惰性求值。
Iterable<int> naturals() sync* {
  var i = 0;
  while (true) {
    yield i++;
  }
}

void main() {
  group('joinWith 常规', () {
    test('在元素之间插入分隔符，且末尾分隔符被去掉', () {
      expect(<int>[1, 2, 3].joinWith(0), <int>[1, 0, 2, 0, 3]);
      expect(<String>['a', 'b'].joinWith('-'), <String>['a', '-', 'b']);
      expect(<String>['a', 'b', 'c', 'd'].joinWith('|'),
          <String>['a', '|', 'b', '|', 'c', '|', 'd']);
      expect(<int>[1].joinWith(0), <int>[1]);
    });
  });

  group('joinWith 空集合', () {
    test('空集合返回空 List', () {
      expect(<int>[].joinWith(0), <int>[]);
      expect(<String>{}.joinWith('-'), <String>[]);
      expect(<int>[].where((e) => e.isEven).joinWith(0), <int>[]);
    });
  });

  group('joinWith 边界与契约', () {
    test('不修改原集合、返回新对象、支持等值分隔符、始终返回 List', () {
      final source = <int>[1, 2, 3];
      source.joinWith(0);
      expect(source, <int>[1, 2, 3]);

      final source2 = <int>[1, 2, 3];
      expect(identical(source2.joinWith(0), source2), false);

      expect(<int>[1, 1].joinWith(1), <int>[1, 1, 1]);

      expect(<int>[].joinWith(0), isA<List<int>>());
    });
  });

  group('excludeIndex 常规', () {
    test('排除指定下标的元素', () {
      expect(<int>[1, 2, 3].excludeIndex(0).toList(), <int>[2, 3]);
      expect(<int>[1, 2, 3].excludeIndex(1).toList(), <int>[1, 3]);
      expect(<int>[1, 2, 3].excludeIndex(2).toList(), <int>[1, 2]);
      expect(<String>['a', 'b', 'c'].excludeIndex(1).toList(), <String>['a', 'c']);
    });
  });

  group('excludeIndex 空集合、惰性与 Iterable 适用性', () {
    test('空集合返回空结果', () {
      expect(<int>[].excludeIndex(0).toList(), <int>[]);
    });

    test('单元素集合排除唯一元素后为空', () {
      expect(<int>[7].excludeIndex(0).toList(), <int>[]);
    });

    test('惰性求值：可作用于无限序列', () {
      // 若 excludeIndex 改为立即求值，本用例会挂起。
      expect(naturals().excludeIndex(0).take(3).toList(), <int>[1, 2, 3]);
    });

    test('返回惰性 Iterable 而非 List', () {
      expect(<int>[1, 2].excludeIndex(0), isNot(isA<List<int>>()));
    });

    test('Set 适用性：保持插入顺序', () {
      expect(<int>{1, 2, 3}.excludeIndex(1).toList(), <int>[1, 3]);
    });

    test('Set 上的 joinWith', () {
      expect(<int>{1, 2, 3}.joinWith(0), <int>[1, 0, 2, 0, 3]);
    });

    test('惰性来源：where 结果上的 excludeIndex', () {
      expect(
        <int>[1, 2, 3, 4].where((e) => e.isEven).excludeIndex(0).toList(),
        <int>[4],
      );
    });
  });

  group('excludeIndex 当前实现的疑似缺陷行为（非约定契约）', () {
    test('越界与负数下标被静默忽略，不抛异常且不改变元素', () {
      // 以下为当前实现的实际输出，不是约定契约。
      expect(<int>[1, 2, 3].excludeIndex(3).toList(), <int>[1, 2, 3]);
      expect(<int>[1, 2, 3].excludeIndex(99).toList(), <int>[1, 2, 3]);
      expect(<int>[1, 2, 3].excludeIndex(-1).toList(), <int>[1, 2, 3]);
      expect(<int>[].excludeIndex(-1).toList(), <int>[]);
    });
  });
}
