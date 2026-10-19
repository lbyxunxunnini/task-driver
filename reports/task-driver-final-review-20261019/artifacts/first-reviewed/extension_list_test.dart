import 'package:facesong_flutter/common/utils/extension_list.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('joinWith', () {
    test('returns an empty list for an empty iterable', () {
      expect(<int>[].joinWith(0), <int>[]);
    });

    test('does not add a separator for a single element', () {
      expect(<int>[7].joinWith(0), <int>[7]);
    });

    test('inserts the separator between elements only', () {
      expect([1, 2, 3].joinWith(0), [1, 0, 2, 0, 3]);
    });

    test('inserts by position even when the separator equals element values', () {
      expect([1, 1, 1].joinWith(1), [1, 1, 1, 1, 1]);
    });

    test('works with a Set iterable', () {
      expect({1, 2, 3}.joinWith(0), [1, 0, 2, 0, 3]);
    });

    test('works with a lazily generated iterable', () {
      expect(Iterable<int>.generate(3, (i) => i).joinWith(-1), [0, -1, 1, -1, 2]);
    });

    test('returns a List instance', () {
      final result = [1, 2].joinWith(0);

      expect(result, isA<List<int>>());
      expect(result.length, 3);
    });

    test('reuses the separator instance instead of copying it', () {
      final separator = Object();

      final result = [Object(), Object()].joinWith(separator);

      expect(result.length, 3);
      expect(identical(result[1], separator), true);
    });
  });

  group('excludeIndex', () {
    test('removes the element at index 0', () {
      expect([1, 2, 3].excludeIndex(0).toList(), [2, 3]);
    });

    test('removes the element at a middle index', () {
      expect([1, 2, 3].excludeIndex(1).toList(), [1, 3]);
    });

    test('removes the element at the last index', () {
      expect([1, 2, 3].excludeIndex(2).toList(), [1, 2]);
    });

    test('returns an empty list when the only element is excluded', () {
      expect(<int>[1].excludeIndex(0).toList(), <int>[]);
    });

    test('removes only the element at the given index when values repeat', () {
      expect([1, 1, 2].excludeIndex(0).toList(), [1, 2]);
    });

    test('returns an empty list for an empty iterable', () {
      expect(<int>[].excludeIndex(0).toList(), <int>[]);
    });

    test('keeps all elements for a negative index', () {
      // Silent "return everything" defense behavior: an in-contract boundary
      // of the current implementation, not a suspected defect.
      expect([1, 2, 3].excludeIndex(-1).toList(), [1, 2, 3]);
    });

    test('keeps all elements when the index equals the length', () {
      // Silent "return everything" defense behavior: an in-contract boundary
      // of the current implementation, not a suspected defect.
      expect([1, 2, 3].excludeIndex(3).toList(), [1, 2, 3]);
    });

    test('keeps all elements when the index is far beyond the length', () {
      // Silent "return everything" defense behavior: an in-contract boundary
      // of the current implementation, not a suspected defect.
      expect([1, 2, 3].excludeIndex(99).toList(), [1, 2, 3]);
    });

    test('returns a lazy Iterable rather than a List', () {
      expect([1, 2].excludeIndex(0), isNot(isA<List<int>>()));
    });

    test('can be iterated more than once', () {
      final iterable = [1, 2, 3].excludeIndex(1);

      expect(iterable.toList(), [1, 3]);
      expect(iterable.toList(), [1, 3]);
    });
  });
}
