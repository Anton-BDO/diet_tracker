"""Чистые доменные расчёты калорийности и макронутриентов."""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from math import isfinite

from backend.domain.errors import ValidationError


_ACTIVITY_FACTORS = (1.2, 1.375, 1.55, 1.725, 1.9)
_GOAL_FACTORS = {"lose": 0.85, "keep": 1.0, "gain": 1.15}
_MACRO_KEYS = ("kcal", "protein", "fat", "carbs")


def _rounded(value, places=0):
    """Округлить десятичное значение по правилу half-up."""
    quantum = Decimal("1") if places == 0 else Decimal("0.1")
    rounded = Decimal(str(value)).quantize(
        quantum, rounding=ROUND_HALF_UP
    )
    return int(rounded) if places == 0 else float(rounded)


def _valid_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return isfinite(value)


def calculate_age(birth_date: str, today: date) -> int:
    """Рассчитать количество полных лет на указанную дату."""
    try:
        born = date.fromisoformat(birth_date)
    except (TypeError, ValueError):
        raise ValidationError(
            "Дата рождения должна быть в формате ГГГГ-ММ-ДД",
            "birth_date",
        ) from None
    if born.isoformat() != birth_date:
        raise ValidationError(
            "Дата рождения должна быть в формате ГГГГ-ММ-ДД",
            "birth_date",
        )
    if born > today:
        raise ValidationError(
            "Дата рождения не может быть в будущем", "birth_date"
        )
    birthday_not_reached = (today.month, today.day) < (born.month, born.day)
    return today.year - born.year - birthday_not_reached


def calculate_bmr(
    sex: str, weight_kg: float, height_cm: float, age: int
) -> float:
    """Рассчитать базовый обмен веществ по формуле Миффлина—Сан Жеора."""
    if sex not in ("male", "female"):
        raise ValidationError(
            "Пол должен быть male или female", "sex"
        )
    if not _valid_number(height_cm) or not 100 <= height_cm <= 250:
        raise ValidationError(
            "Рост должен быть от 100 до 250 см", "height_cm"
        )
    if not _valid_number(weight_kg) or not 30 <= weight_kg <= 300:
        raise ValidationError(
            "Вес должен быть от 30 до 300 кг", "weight_kg"
        )
    invalid_age = isinstance(age, bool) or not isinstance(age, int)
    if invalid_age or not 14 <= age <= 100:
        raise ValidationError(
            "Возраст должен быть от 14 до 100 лет", "age"
        )
    offset = 5 if sex == "male" else -161
    return 10 * weight_kg + 6.25 * height_cm - 5 * age + offset


def calculate_tdee(bmr: float, activity: float) -> float:
    """Рассчитать суточный расход энергии с учётом активности."""
    if activity not in _ACTIVITY_FACTORS:
        raise ValidationError(
            "Недопустимый коэффициент активности", "activity"
        )
    return bmr * activity


def calculate_target_calories(tdee: float, goal: str) -> int:
    """Рассчитать целевую калорийность для выбранной цели."""
    if goal not in _GOAL_FACTORS:
        raise ValidationError(
            "Цель должна быть lose, keep или gain", "goal"
        )
    return _rounded(tdee * _GOAL_FACTORS[goal])


def calculate_macros(target_kcal: int) -> dict:
    """Рассчитать целевые граммы белков, жиров и углеводов."""
    return {
        "protein": _rounded(target_kcal * 0.30 / 4),
        "fat": _rounded(target_kcal * 0.30 / 9),
        "carbs": _rounded(target_kcal * 0.40 / 4),
    }


def calculate_daily_targets(
    sex, weight_kg, height_cm, age, activity, goal
) -> dict:
    """Собрать суточную норму из доменных расчётов."""
    bmr = calculate_bmr(sex, weight_kg, height_cm, age)
    tdee = calculate_tdee(bmr, activity)
    kcal = calculate_target_calories(tdee, goal)
    return {"kcal": kcal, **calculate_macros(kcal)}


def calculate_portion(per_100g: dict, grams: float) -> dict:
    """Рассчитать КБЖУ порции заданной массы."""
    if not _valid_number(grams) or not 1 <= grams <= 5000:
        raise ValidationError(
            "Масса порции должна быть от 1 до 5000 г", "grams"
        )
    return {
        key: _rounded(per_100g[key] * grams / 100, 1)
        for key in _MACRO_KEYS
    }
