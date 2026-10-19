import 'package:facesong_flutter/common/utils/extension_duration.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Duration.mmss 常规格式化', () {
    test('formats common durations as mm:ss', () {
      expect(Duration.zero.mmss, '00:00');
      expect(const Duration(seconds: 5).mmss, '00:05');
      expect(const Duration(seconds: 59).mmss, '00:59');
      expect(const Duration(seconds: 60).mmss, '01:00');
      expect(const Duration(seconds: 61).mmss, '01:01');
      expect(const Duration(seconds: 599).mmss, '09:59');
      expect(const Duration(seconds: 3599).mmss, '59:59');
      expect(const Duration(minutes: 12, seconds: 34).mmss, '12:34');
    });
  });

  group('Duration.mmss 边界：小时不进位与超两位不裁剪', () {
    test('keeps minutes beyond 59 without carrying into hours', () {
      expect(const Duration(hours: 1).mmss, '60:00');
      expect(const Duration(hours: 1, minutes: 40).mmss, '100:00');
      expect(const Duration(minutes: 99, seconds: 59).mmss, '99:59');
    });
  });

  group('Duration.mmss 边界：亚秒向零截断', () {
    test('truncates sub-second part toward zero', () {
      expect(const Duration(milliseconds: 999).mmss, '00:00');
      expect(const Duration(milliseconds: 1500).mmss, '00:01');
      expect(const Duration(milliseconds: 1999).mmss, '00:01');
      expect(const Duration(seconds: 59, milliseconds: 999).mmss, '00:59');
    });
  });

  group('Duration.mmss 当前实现的疑似缺陷行为（非约定契约）', () {
    test('negative durations produce odd but deterministic output', () {
      // 以下为当前实现的实际输出，不是约定契约
      expect(const Duration(seconds: -5).mmss, '00:55');
      expect(const Duration(seconds: -1).mmss, '00:59');
      expect(const Duration(seconds: -65).mmss, '-1:55');
    });
  });
}
