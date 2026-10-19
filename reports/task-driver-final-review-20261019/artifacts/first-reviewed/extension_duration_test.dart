import 'package:facesong_flutter/common/utils/extension_duration.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('mmss', () {
    test('formats zero duration', () {
      expect(Duration.zero.mmss, '00:00');
    });

    test('formats seconds below one minute', () {
      expect(Duration(seconds: 5).mmss, '00:05');
      expect(Duration(seconds: 59).mmss, '00:59');
    });

    test('formats one minute boundaries', () {
      expect(Duration(seconds: 60).mmss, '01:00');
      expect(Duration(seconds: 61).mmss, '01:01');
    });

    test('formats 59 minutes 59 seconds', () {
      expect(Duration(minutes: 59, seconds: 59).mmss, '59:59');
    });

    test('formats one hour as 60 minutes', () {
      expect(Duration(hours: 1).mmss, '60:00');
    });

    test('does not cap minutes at two digits', () {
      expect(Duration(minutes: 100).mmss, '100:00');
    });
  });

  group('mmss - boundary', () {
    test('truncates milliseconds below one second', () {
      expect(Duration(milliseconds: 999).mmss, '00:00');
    });

    test('truncates sub-second remainder instead of rounding', () {
      expect(Duration(milliseconds: 1500).mmss, '00:01');
      expect(Duration(milliseconds: 59999).mmss, '00:59');
    });

    test('does not cap hours at two digits', () {
      expect(Duration(hours: 100).mmss, '6000:00');
    });
  });

  group('mmss - negative duration (non-contract)', () {
    // These assertions only record the output of the current implementation,
    // they are NOT a contract. The rendered value for negative durations is
    // counter-intuitive (e.g. -65 seconds renders as '-1:55'), so if the
    // negative-duration behavior is ever fixed, this group must be updated too.
    test('records current output for -5 seconds', () {
      expect(Duration(seconds: -5).mmss, '00:55');
    });

    test('records current output for -65 seconds', () {
      expect(Duration(seconds: -65).mmss, '-1:55');
    });
  });
}
