"""Расчёт текущей серии и рекорда успешных дней."""
from datetime import date

from backend.domain.models import validate_date
from backend.domain.nutrition import sum_nutrients
from backend.domain.streaks import (
    current_streak,
    is_success_day,
    record_streak,
)


class StreakService:
    """Серии успешных дней по всей истории дневника."""

    def __init__(self, entries, profile_service):
        self._entries = entries
        self._profiles = profile_service

    def get_streak(self, today_raw, user_id):
        """Текущая серия и рекорд; today можно передать для тестов."""
        today = resolve_today(today_raw)
        _, norm = self._profiles.get_profile(user_id)
        history = self._entries.get_all_by_user(user_id)
        successes = success_map(history, norm["kcal"])
        return {
            "current": current_streak(successes, today),
            "record": record_streak(successes),
        }


def resolve_today(today_raw):
    """Проверить параметр today или взять текущую дату сервера."""
    if today_raw is None:
        return date.today()
    return validate_date(today_raw, "today")


def entries_by_date(entries):
    """Сгруппировать записи дневника по дате."""
    by_date = {}
    for entry in entries:
        by_date.setdefault(entry.date, []).append(entry)
    return by_date


def success_map(entries, norm_kcal):
    """Словарь дата -> успешность дня по текущей норме."""
    return {
        day: is_success_day(
            sum_nutrients(items)["kcal"],
            norm_kcal,
            len(items),
        )
        for day, items in entries_by_date(entries).items()
    }
