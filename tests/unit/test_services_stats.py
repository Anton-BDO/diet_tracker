"""Тесты сервисов серий и статистики калорий."""
import pytest

from backend.domain.errors import NotFoundError, ValidationError
from backend.domain.models import FoodEntry, User
from backend.services.stats import CaloriesStatsService, parse_days
from backend.services.streak import StreakService

USER_ID = "6521a3b5c9e8d761a2b3c0ff"

USER = User(
    id=USER_ID,
    email="user@example.com",
    password_hash="pbkdf2_sha256$1$c2FsdA==$ZGlnZXN0",
    name="Алексей",
    sex="male",
    birth_date="1996-03-15",
    height_cm=180,
    weight_kg=80,
    activity=1.55,
    goal="lose",
)

NORM_KCAL = 2345


def _entry(date, grams, kcal_per_100g=100):
    """Запись с kcal = grams при ккал на 100 г = 100."""
    kcal = round(kcal_per_100g * grams / 100, 1)
    return FoodEntry(
        user_id=USER_ID,
        product_id="6521a3b5c9e8d761a2b3c001",
        product_name="Продукт",
        grams=grams,
        meal="lunch",
        date=date,
        kcal=kcal,
        protein=1.0,
        fat=1.0,
        carbs=1.0,
    )


class FakeEntries:
    """Записи, заданные списком объектов."""

    def __init__(self, items=()):
        self.items = list(items)

    def get_all_by_user(self, user_id):
        return list(self.items)

    def get_by_user_and_period(self, user_id, date_from, date_to):
        return [
            entry for entry in self.items
            if date_from <= entry.date <= date_to
        ]


class FakeProfiles:
    def get_profile(self, user_id):
        if user_id != USER_ID:
            raise NotFoundError("Пользователь не найден")
        return USER, {"kcal": NORM_KCAL, "protein": 176, "fat": 78,
                      "carbs": 235}


def _streak_service(items=()):
    return StreakService(FakeEntries(items), FakeProfiles())


def _stats_service(items=()):
    return CaloriesStatsService(FakeEntries(items), FakeProfiles())


# Успешный день: записи есть и калории в пределах 2110.5–2579.5.


def test_streak_counts_days_ending_yesterday():
    entries = [_entry("2026-10-18", 2200), _entry("2026-10-19", 2200)]
    service = _streak_service(entries)

    result = service.get_streak("2026-10-20", USER_ID)

    assert result == {"current": 2, "record": 2}


def test_streak_counts_days_ending_today():
    entries = [_entry("2026-10-20", 2200)]
    service = _streak_service(entries)

    assert service.get_streak("2026-10-20", USER_ID)["current"] == 1


def test_missed_day_breaks_streak_but_record_stays():
    entries = [_entry("2026-10-16", 2200), _entry("2026-10-17", 2200),
               _entry("2026-10-19", 2200)]
    service = _streak_service(entries)

    result = service.get_streak("2026-10-20", USER_ID)

    assert result == {"current": 1, "record": 2}


def test_failed_today_keeps_yesterday_ending_streak():
    entries = [_entry("2026-10-19", 2200), _entry("2026-10-20", 4000)]
    service = _streak_service(entries)

    result = service.get_streak("2026-10-20", USER_ID)

    assert result == {"current": 1, "record": 1}


def test_failed_day_between_successes_breaks_streak():
    entries = [_entry("2026-10-19", 4000), _entry("2026-10-20", 2200)]
    service = _streak_service(entries)

    result = service.get_streak("2026-10-20", USER_ID)

    assert result["current"] == 1


def test_streak_invalid_today_is_validation_error():
    service = _streak_service()

    with pytest.raises(ValidationError) as exc_info:
        service.get_streak("2026-13-40", USER_ID)

    assert exc_info.value.field == "today"


def test_streak_without_history_is_zero():
    assert _streak_service().get_streak("2026-10-20", USER_ID) == {
        "current": 0, "record": 0,
    }


def test_stats_include_empty_days_in_order():
    entries = [_entry("2026-10-20", 2200)]
    service = _stats_service(entries)

    result = service.get_calories(3, "2026-10-20", USER_ID)

    assert result["norm_kcal"] == NORM_KCAL
    assert [(day["date"], day["kcal"]) for day in result["days"]] == [
        ("2026-10-18", 0.0),
        ("2026-10-19", 0.0),
        ("2026-10-20", 2200.0),
    ]
    assert [day["is_success"] for day in result["days"]] == [
        False, False, True,
    ]


def test_stats_sum_day_entries_once():
    entries = [_entry("2026-10-20", 1000), _entry("2026-10-20", 1200)]
    service = _stats_service(entries)

    result = service.get_calories(1, "2026-10-20", USER_ID)

    assert result["days"][0]["kcal"] == 2200.0


@pytest.mark.parametrize("value,expected", [
    (None, 7),
    ("1", 1),
    ("90", 90),
    (5, 5),
])
def test_parse_days_valid(value, expected):
    assert parse_days(value) == expected


@pytest.mark.parametrize("value", ["7.5", "abc", "0", "91", "", True,
                                   7.5, 1.9, -3, "²", "①"])
def test_parse_days_invalid(value):
    with pytest.raises(ValidationError) as exc_info:
        parse_days(value)

    assert exc_info.value.field == "days"


class _VariableProfiles(FakeProfiles):
    """Профиль с задаваемой нормой калорий."""

    def __init__(self, kcal):
        self.kcal = kcal

    def get_profile(self, user_id):
        if user_id != USER_ID:
            raise NotFoundError("Пользователь не найден")
        return USER, {"kcal": self.kcal, "protein": 176, "fat": 78,
                      "carbs": 235}


def _streak_with_norm(items, kcal):
    return StreakService(FakeEntries(items), _VariableProfiles(kcal))


def test_past_days_are_rejudged_by_current_norm():
    """Прошлые дни оцениваются по текущей норме, а не старой."""
    entries = [_entry("2026-10-19", 2300)]   # 98% от 2345, 115% от 2000

    assert _streak_with_norm(entries, 2345).get_streak(
        "2026-10-20", USER_ID,
    )["current"] == 1
    assert _streak_with_norm(entries, 2000).get_streak(
        "2026-10-20", USER_ID,
    )["current"] == 0
