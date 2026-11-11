"""Статистика калорий по дням для графиков."""
from datetime import timedelta

from backend.domain.errors import ValidationError
from backend.domain.nutrition import sum_nutrients
from backend.domain.streaks import is_success_day
from backend.services.streak import entries_by_date, resolve_today

_MAX_DAYS = 90


class CaloriesStatsService:
    """Калории по дням за период, включая дни без записей."""

    def __init__(self, entries, profile_service):
        self._entries = entries
        self._profiles = profile_service

    def get_calories(self, days_raw, today_raw, user_id):
        """Вернуть каждый день периода с суммой калорий и успехом."""
        days = parse_days(days_raw)
        today = resolve_today(today_raw)
        date_from = today - timedelta(days=days - 1)

        _, norm = self._profiles.get_profile(user_id)
        history = self._entries.get_by_user_and_period(
            user_id,
            date_from.isoformat(),
            today.isoformat(),
        )
        grouped = entries_by_date(history)

        result_days = []
        for offset in range(days):
            day = date_from + timedelta(days=offset)
            key = day.isoformat()
            items = grouped.get(key, [])
            kcal = sum_nutrients(items)["kcal"] if items else 0.0
            result_days.append({
                "date": key,
                "kcal": kcal,
                "is_success": is_success_day(
                    kcal, norm["kcal"], len(items),
                ),
            })

        return {"norm_kcal": norm["kcal"], "days": result_days}


def parse_days(value):
    """Разобрать days: целое от 1 до 90, по умолчанию 7."""
    if value is None:
        return 7
    if isinstance(value, bool):
        raise ValidationError("days должен быть целым числом", "days")
    if isinstance(value, int):
        days = value
    elif (
        isinstance(value, str)
        and value.isascii()
        and value.isdigit()
    ):
        days = int(value)
    else:
        raise ValidationError("days должен быть целым числом", "days")
    if not 1 <= days <= _MAX_DAYS:
        raise ValidationError(
            f"days должен быть от 1 до {_MAX_DAYS}",
            "days",
        )
    return days
