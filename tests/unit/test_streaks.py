"""Tests for nutrition diary streak calculations."""

from datetime import date

from backend.domain.streaks import (
    current_streak,
    is_success_day,
    record_streak,
)


def test_success_day_requires_entries_and_inclusive_calorie_bounds():
    assert is_success_day(900, 1000, 1)
    assert is_success_day(1100, 1000, 1)
    assert not is_success_day(899, 1000, 1)
    assert not is_success_day(1000, 1000, 0)


def test_current_streak_can_end_today_or_yesterday():
    today = date(2026, 10, 27)
    assert current_streak({"2026-10-25": True, "2026-10-26": True}, today) == 2
    assert current_streak({"2026-10-24": True, "2026-10-25": True,
                           "2026-10-26": True}, today) == 3
    assert current_streak({"2026-10-27": True, "2026-10-26": True}, today) == 2


def test_current_streak_breaks_on_failure_or_missing_date_and_ignores_future():
    today = date(2026, 10, 27)
    assert current_streak({}, today) == 0
    assert current_streak(
        {"2026-10-26": False, "2026-10-27": False}, today
    ) == 0
    assert current_streak({"2026-10-24": True, "2026-10-26": True}, today) == 1
    assert current_streak({"2026-10-28": True}, today) == 0


def test_record_streak_is_historical_and_missing_days_break_series():
    assert record_streak({}) == 0
    assert record_streak({"2020-01-01": True, "2020-01-02": True,
                          "2020-01-04": True, "2020-01-05": True,
                          "2020-01-06": True}) == 3
    assert record_streak({"2035-01-01": True, "2035-01-02": True}) == 2
    assert record_streak({"2020-01-01": True, "2020-01-02": False,
                          "2020-01-03": True}) == 1
