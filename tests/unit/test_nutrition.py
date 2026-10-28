"""Tests for pure nutrition domain calculations."""

from datetime import date

import pytest

from backend.domain.errors import ValidationError
from backend.domain.nutrition import (
    calculate_age,
    calculate_bmr,
    calculate_daily_targets,
    calculate_macros,
    calculate_portion,
    calculate_target_calories,
    calculate_tdee,
)


def test_calculate_age_boundaries_and_invalid_dates():
    assert calculate_age("2000-10-27", date(2026, 10, 27)) == 26
    assert calculate_age("2000-10-28", date(2026, 10, 27)) == 25
    with pytest.raises(ValidationError) as error:
        calculate_age("2027-01-01", date(2026, 10, 27))
    assert error.value.field == "birth_date"
    with pytest.raises(ValidationError):
        calculate_age("2000-2-01", date(2026, 10, 27))


@pytest.mark.parametrize(
    "sex,weight,height,age,expected",
    [("male", 80, 180, 30, 1780), ("female", 60, 165, 25, 1345.25)],
)
def test_calculate_bmr(sex, weight, height, age, expected):
    assert calculate_bmr(sex, weight, height, age) == expected


@pytest.mark.parametrize("activity", [1.2, 1.375, 1.55, 1.725, 1.9])
def test_calculate_tdee_accepts_all_activity_factors(activity):
    assert calculate_tdee(100, activity) == 100 * activity


@pytest.mark.parametrize(
    "goal,factor", [("lose", .85), ("keep", 1), ("gain", 1.15)]
)
def test_target_calories_uses_half_up(goal, factor):
    assert calculate_target_calories(100, goal) == int(factor * 100 + .5)
    assert calculate_target_calories(10, "keep") == 10
    assert calculate_target_calories(10, "lose") == 9


def test_calculate_macros_and_daily_targets_match_examples():
    assert calculate_macros(2345) == {"protein": 176, "fat": 78, "carbs": 235}
    assert calculate_daily_targets("male", 80, 180, 30, 1.55, "lose") == {
        "kcal": 2345, "protein": 176, "fat": 78, "carbs": 235,
    }
    assert calculate_daily_targets("female", 60, 165, 25, 1.2, "keep") == {
        "kcal": 1614, "protein": 121, "fat": 54, "carbs": 161,
    }


@pytest.mark.parametrize(
    "args,field",
    [(("other", 80, 180, 30), "sex"), (("male", 29, 180, 30), "weight_kg"),
     (("male", 80, 99, 30), "height_cm"), (("male", 80, 180, 13), "age")],
)
def test_bmr_validation(args, field):
    with pytest.raises(ValidationError) as error:
        calculate_bmr(*args)
    assert error.value.field == field


@pytest.mark.parametrize(
    "weight,height,age",
    [(30, 100, 14), (300, 250, 100)],
)
def test_bmr_validation_boundaries_are_inclusive(weight, height, age):
    assert isinstance(calculate_bmr("male", weight, height, age), float)


@pytest.mark.parametrize(
    "args,field",
    [(("male", 301, 180, 30), "weight_kg"),
     (("male", 80, 251, 30), "height_cm"),
     (("male", 80, 180, 101), "age")],
)
def test_bmr_rejects_values_above_upper_bounds(args, field):
    with pytest.raises(ValidationError) as error:
        calculate_bmr(*args)
    assert error.value.field == field


def test_activity_and_goal_validation():
    with pytest.raises(ValidationError) as error:
        calculate_tdee(100, 1.3)
    assert error.value.field == "activity"
    with pytest.raises(ValidationError) as error:
        calculate_target_calories(100, "bulk")
    assert error.value.field == "goal"


def test_calculate_portion_rounding_and_limits():
    values = {"kcal": 123, "protein": 10.05, "fat": 2.25, "carbs": 3.35}
    assert calculate_portion(values, 100) == {
        "kcal": 123.0, "protein": 10.1, "fat": 2.3, "carbs": 3.4,
    }
    assert calculate_portion(values, 1)["kcal"] == 1.2
    assert calculate_portion(values, 5000)["kcal"] == 6150.0
    for grams in (0, 5001):
        with pytest.raises(ValidationError) as error:
            calculate_portion(values, grams)
        assert error.value.field == "grams"
