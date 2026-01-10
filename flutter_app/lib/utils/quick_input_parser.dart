/// 빠른 입력 텍스트를 파싱하여 일정 정보를 추출하는 유틸리티
///
/// 사용 예시:
/// - "2/11 2시 집행부 회의" → 2월 11일 14:00, "집행부 회의"
/// - "내일 오후 3시 팀 미팅" → 내일 15:00, "팀 미팅"
/// - "다음주 월요일 10시 주간회의" → 다음주 월요일 10:00, "주간회의"

/// 파싱 결과 데이터 클래스
class QuickInputResult {
  final DateTime? dateTime;
  final String title;
  final bool hasDate;
  final bool hasTime;

  const QuickInputResult({
    this.dateTime,
    required this.title,
    this.hasDate = false,
    this.hasTime = false,
  });

  @override
  String toString() {
    return 'QuickInputResult(dateTime: $dateTime, title: $title, hasDate: $hasDate, hasTime: $hasTime)';
  }
}

class QuickInputParser {
  // 날짜 패턴
  static final RegExp _slashDatePattern = RegExp(r'(\d{1,2})/(\d{1,2})');
  static final RegExp _koreanDatePattern = RegExp(r'(\d{1,2})월\s*(\d{1,2})일');
  static final RegExp _relativeDatePattern = RegExp(r'(오늘|내일|모레)');
  static final RegExp _weekdayPattern = RegExp(r'(다음주|이번주|다다음주)?\s*(월|화|수|목|금|토|일)요일');

  // 시간 패턴 (순서 중요: 구체적인 것 먼저)
  static final RegExp _ampmHourPattern = RegExp(r'(오전|오후)\s*(\d{1,2})시');
  static final RegExp _ampmHourMinPattern = RegExp(r'(오전|오후)\s*(\d{1,2})시\s*(\d{1,2})분');
  static final RegExp _hourHalfPattern = RegExp(r'(\d{1,2})시\s*반');
  static final RegExp _hourMinPattern = RegExp(r'(\d{1,2})시\s*(\d{1,2})분');
  static final RegExp _hourOnlyPattern = RegExp(r'(\d{1,2})시(?!\s*반|\s*\d)');
  static final RegExp _colonTimePattern = RegExp(r'(\d{1,2}):(\d{2})');

  /// 메인 파싱 메서드
  static QuickInputResult parse(String input) {
    if (input.trim().isEmpty) {
      return const QuickInputResult(title: '새 일정');
    }

    String remaining = input.trim();
    DateTime baseDate = DateTime.now();
    bool hasDate = false;
    bool hasTime = false;
    int? hour;
    int? minute;

    // 1. 날짜 파싱
    final dateResult = _parseDate(remaining);
    if (dateResult != null) {
      baseDate = dateResult.date;
      remaining = _removeMatch(remaining, dateResult.match);
      hasDate = true;
    }

    // 2. 시간 파싱
    final timeResult = _parseTime(remaining);
    if (timeResult != null) {
      hour = timeResult.hour;
      minute = timeResult.minute;
      remaining = _removeMatch(remaining, timeResult.match);
      hasTime = true;
    }

    // 3. 최종 DateTime 조합
    DateTime? finalDateTime;
    if (hasDate || hasTime) {
      finalDateTime = DateTime(
        baseDate.year,
        baseDate.month,
        baseDate.day,
        hour ?? (DateTime.now().hour + 1),
        minute ?? 0,
      );
    }

    // 4. 남은 텍스트 정리 → 제목
    String title = _cleanTitle(remaining);
    if (title.isEmpty) {
      title = '새 일정';
    }

    return QuickInputResult(
      dateTime: finalDateTime,
      title: title,
      hasDate: hasDate,
      hasTime: hasTime,
    );
  }

  /// 날짜 파싱
  static _DateResult? _parseDate(String input) {
    // 상대 날짜: 오늘, 내일, 모레
    final relativeMatch = _relativeDatePattern.firstMatch(input);
    if (relativeMatch != null) {
      final keyword = relativeMatch.group(1)!;
      final date = _getRelativeDate(keyword);
      return _DateResult(date, relativeMatch);
    }

    // 요일: 다음주 월요일, 이번주 금요일
    final weekdayMatch = _weekdayPattern.firstMatch(input);
    if (weekdayMatch != null) {
      final prefix = weekdayMatch.group(1); // 다음주, 이번주, null
      final weekday = weekdayMatch.group(2)!; // 월, 화, 수...
      final date = _getWeekdayDate(prefix, weekday);
      return _DateResult(date, weekdayMatch);
    }

    // 슬래시 형식: 2/11, 02/11
    final slashMatch = _slashDatePattern.firstMatch(input);
    if (slashMatch != null) {
      final month = int.parse(slashMatch.group(1)!);
      final day = int.parse(slashMatch.group(2)!);
      final date = _buildDate(month, day);
      return _DateResult(date, slashMatch);
    }

    // 한글 형식: 2월 11일, 2월11일
    final koreanMatch = _koreanDatePattern.firstMatch(input);
    if (koreanMatch != null) {
      final month = int.parse(koreanMatch.group(1)!);
      final day = int.parse(koreanMatch.group(2)!);
      final date = _buildDate(month, day);
      return _DateResult(date, koreanMatch);
    }

    return null;
  }

  /// 시간 파싱
  static _TimeResult? _parseTime(String input) {
    // 오전/오후 + 시분: 오후 2시 30분
    final ampmMinMatch = _ampmHourMinPattern.firstMatch(input);
    if (ampmMinMatch != null) {
      final ampm = ampmMinMatch.group(1)!;
      int hour = int.parse(ampmMinMatch.group(2)!);
      final minute = int.parse(ampmMinMatch.group(3)!);
      hour = _convertAmPmHour(hour, ampm);
      return _TimeResult(hour, minute, ampmMinMatch);
    }

    // 오전/오후 + 시: 오후 2시
    final ampmMatch = _ampmHourPattern.firstMatch(input);
    if (ampmMatch != null) {
      final ampm = ampmMatch.group(1)!;
      int hour = int.parse(ampmMatch.group(2)!);
      hour = _convertAmPmHour(hour, ampm);
      return _TimeResult(hour, 0, ampmMatch);
    }

    // 시:분 형식: 14:30, 2:30
    final colonMatch = _colonTimePattern.firstMatch(input);
    if (colonMatch != null) {
      int hour = int.parse(colonMatch.group(1)!);
      final minute = int.parse(colonMatch.group(2)!);
      hour = _normalizeHour(hour);
      return _TimeResult(hour, minute, colonMatch);
    }

    // 시 반: 2시 반, 2시반
    final halfMatch = _hourHalfPattern.firstMatch(input);
    if (halfMatch != null) {
      int hour = int.parse(halfMatch.group(1)!);
      hour = _normalizeHour(hour);
      return _TimeResult(hour, 30, halfMatch);
    }

    // 시분: 2시 30분
    final hourMinMatch = _hourMinPattern.firstMatch(input);
    if (hourMinMatch != null) {
      int hour = int.parse(hourMinMatch.group(1)!);
      final minute = int.parse(hourMinMatch.group(2)!);
      hour = _normalizeHour(hour);
      return _TimeResult(hour, minute, hourMinMatch);
    }

    // 시만: 2시, 14시
    final hourMatch = _hourOnlyPattern.firstMatch(input);
    if (hourMatch != null) {
      int hour = int.parse(hourMatch.group(1)!);
      hour = _normalizeHour(hour);
      return _TimeResult(hour, 0, hourMatch);
    }

    return null;
  }

  /// 업무시간 기준 시간 정규화
  /// 1-8시 → 오후(+12), 9-12시 → 오전
  static int _normalizeHour(int hour) {
    if (hour >= 13 && hour <= 23) {
      // 이미 24시간제: 13~23시 그대로
      return hour;
    } else if (hour >= 1 && hour <= 8) {
      // 1~8시 → 오후로 해석 (13~20시)
      return hour + 12;
    } else {
      // 9~12시 → 오전 그대로
      return hour;
    }
  }

  /// 오전/오후 명시적 변환
  static int _convertAmPmHour(int hour, String ampm) {
    if (ampm == '오후') {
      return hour < 12 ? hour + 12 : hour;
    } else {
      return hour == 12 ? 0 : hour;
    }
  }

  /// 상대 날짜 계산
  static DateTime _getRelativeDate(String keyword) {
    final now = DateTime.now();
    switch (keyword) {
      case '오늘':
        return now;
      case '내일':
        return now.add(const Duration(days: 1));
      case '모레':
        return now.add(const Duration(days: 2));
      default:
        return now;
    }
  }

  /// 요일 기준 날짜 계산
  static DateTime _getWeekdayDate(String? prefix, String weekday) {
    final now = DateTime.now();
    final targetWeekday = _weekdayToInt(weekday);
    final currentWeekday = now.weekday;

    int daysToAdd;

    if (prefix == '다음주') {
      // 다음주 해당 요일
      daysToAdd = (7 - currentWeekday) + targetWeekday;
    } else if (prefix == '다다음주') {
      // 다다음주 해당 요일
      daysToAdd = (14 - currentWeekday) + targetWeekday;
    } else {
      // 이번주 또는 생략 → 이번주 해당 요일 (지났으면 다음주)
      daysToAdd = targetWeekday - currentWeekday;
      if (daysToAdd <= 0) {
        daysToAdd += 7; // 이미 지난 요일이면 다음주
      }
    }

    return now.add(Duration(days: daysToAdd));
  }

  static int _weekdayToInt(String weekday) {
    const weekdays = {'월': 1, '화': 2, '수': 3, '목': 4, '금': 5, '토': 6, '일': 7};
    return weekdays[weekday] ?? 1;
  }

  /// 월/일로 DateTime 생성 (과거면 내년으로)
  static DateTime _buildDate(int month, int day) {
    final now = DateTime.now();
    var date = DateTime(now.year, month, day);

    // 이미 지난 날짜면 내년으로
    if (date.isBefore(DateTime(now.year, now.month, now.day))) {
      date = DateTime(now.year + 1, month, day);
    }

    return date;
  }

  /// 매치된 패턴을 문자열에서 제거
  static String _removeMatch(String input, Match match) {
    return input.replaceRange(match.start, match.end, ' ');
  }

  /// 제목 정리 (불필요한 공백 제거)
  static String _cleanTitle(String input) {
    return input
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();
  }
}

// 내부 헬퍼 클래스
class _DateResult {
  final DateTime date;
  final Match match;
  _DateResult(this.date, this.match);
}

class _TimeResult {
  final int hour;
  final int minute;
  final Match match;
  _TimeResult(this.hour, this.minute, this.match);
}
