"""Чистые функции расчёта успешных дней и серий."""

from datetime import date, timedelta


def is_success_day(
    eaten_kcal: float, target_kcal: int, entries_count: int
) -> bool:
    """Проверить наличие записей и попадание калорий в диапазон ±10%."""
    lower_bound = target_kcal * 0.9
    upper_bound = target_kcal * 1.1
    return entries_count > 0 and lower_bound <= eaten_kcal <= upper_bound


def _successful_dates(success_by_date):
    return sorted(
        date.fromisoformat(day)
        for day, success in success_by_date.items()
        if success
    )


def current_streak(success_by_date: dict, today: date) -> int:
    """Посчитать текущую серию, заканчивающуюся сегодня или вчера."""
    yesterday = today - timedelta(days=1)
    if success_by_date.get(today.isoformat()) is True:
        cursor = today
    elif success_by_date.get(yesterday.isoformat()) is True:
        cursor = yesterday
    else:
        return 0

    count = 0
    while success_by_date.get(cursor.isoformat()) is True:
        count += 1
        cursor -= timedelta(days=1)
    return count


def record_streak(success_by_date: dict) -> int:
    """Найти максимальную историческую серию успешных дней."""
    dates = _successful_dates(success_by_date)
    if not dates:
        return 0

    longest = current = 1
    for previous, current_date in zip(dates, dates[1:]):
        if current_date == previous + timedelta(days=1):
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest
