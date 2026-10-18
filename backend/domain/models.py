"""Доменные модели приложения diet_tracker.

Модели не зависят от MongoDB и PyMongo.
Идентификаторы внутри моделей представлены строками.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from math import isfinite
from typing import Literal, Optional


Gender = Literal["male", "female"]
Activity = Literal["sedentary", "light", "moderate", "high", "extreme"]
Goal = Literal["lose", "maintain", "gain"]
Meal = Literal["breakfast", "lunch", "dinner", "snack"]


def utc_now() -> datetime:
    """Вернуть текущее время в UTC."""
    return datetime.now(timezone.utc)


def _require_nonempty(value: str, field_name: str) -> None:
    """Проверить, что значение является непустой строкой."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_positive(value: float, field_name: str) -> None:
    """Проверить, что число конечное и больше нуля."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{field_name} must be a positive number")


def _require_nonnegative(value: float, field_name: str) -> None:
    """Проверить, что число конечное и неотрицательное."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or value < 0
    ):
        raise ValueError(
            f"{field_name} must be a non-negative number"
        )


def _validate_date(value: str) -> None:
    """Проверить формат даты YYYY-MM-DD и существование даты."""
    _require_nonempty(value, "date")

    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(
            "date must use YYYY-MM-DD format"
        ) from exc

    if parsed.strftime("%Y-%m-%d") != value:
        raise ValueError("date must use YYYY-MM-DD format")


@dataclass
class MacroTargets:
    """Суточные цели макронутриентов в граммах."""

    protein: float
    fat: float
    carbs: float

    def __post_init__(self) -> None:
        for name in ("protein", "fat", "carbs"):
            value = getattr(self, name)
            _require_nonnegative(value, f"macros.{name}")
            setattr(self, name, float(value))


@dataclass
class User:
    """Пользователь и рассчитанные суточные нормы питания."""

    email: str
    password_hash: str
    name: str
    gender: Gender
    age: int
    height_cm: float
    weight_kg: float
    activity: Activity
    goal: Goal
    daily_calories: int
    macros: MacroTargets
    id: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_nonempty(self.email, "email")
        _require_nonempty(self.password_hash, "password_hash")
        _require_nonempty(self.name, "name")

        self.email = self.email.strip().lower()
        self.name = self.name.strip()

        if "@" not in self.email or self.email.startswith("@"):
            raise ValueError("email must be valid")

        if self.gender not in ("male", "female"):
            raise ValueError("gender must be 'male' or 'female'")

        allowed_activity = (
            "sedentary", "light", "moderate", "high", "extreme"
        )
        if self.activity not in allowed_activity:
            raise ValueError("unsupported activity")

        if self.goal not in ("lose", "maintain", "gain"):
            raise ValueError("goal must be 'lose', 'maintain' or 'gain'")

        if (
            isinstance(self.age, bool)
            or not isinstance(self.age, int)
            or self.age < 1
        ):
            raise ValueError("age must be a positive integer")

        _require_positive(self.height_cm, "height_cm")
        _require_positive(self.weight_kg, "weight_kg")

        if (
            isinstance(self.daily_calories, bool)
            or not isinstance(self.daily_calories, int)
            or self.daily_calories < 0
        ):
            raise ValueError(
                "daily_calories must be a non-negative integer"
            )

        if isinstance(self.macros, dict):
            self.macros = MacroTargets(**self.macros)

        if not isinstance(self.macros, MacroTargets):
            raise ValueError("macros must be MacroTargets")

        if self.id is not None:
            _require_nonempty(self.id, "id")

        self.height_cm = float(self.height_cm)
        self.weight_kg = float(self.weight_kg)


@dataclass
class Product:
    """Продукт из общего справочника или пользовательская позиция."""

    name: str
    calories: float
    protein: float
    fat: float
    carbs: float
    is_custom: bool = False
    owner_id: Optional[str] = None
    id: Optional[str] = None
    name_lower: str = ""
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_nonempty(self.name, "name")
        self.name = self.name.strip()
        self.name_lower = self.name.casefold()

        for attr in ("calories", "protein", "fat", "carbs"):
            value = getattr(self, attr)
            _require_nonnegative(value, attr)
            setattr(self, attr, float(value))

        if not isinstance(self.is_custom, bool):
            raise ValueError("is_custom must be bool")

        if self.is_custom:
            _require_nonempty(self.owner_id, "owner_id")
        elif self.owner_id is not None:
            raise ValueError(
                "system product must have owner_id=None"
            )

        if self.id is not None:
            _require_nonempty(self.id, "id")


@dataclass
class FoodEntry:
    """Запись дневника питания с сохранёнными нутриентами порции."""

    user_id: str
    product_id: str
    product_name: str
    grams: float
    calories: float
    protein: float
    fat: float
    carbs: float
    meal: Meal
    date: str
    id: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        for name in ("user_id", "product_id", "product_name"):
            _require_nonempty(getattr(self, name), name)

        _require_positive(self.grams, "grams")

        for attr in ("calories", "protein", "fat", "carbs"):
            value = getattr(self, attr)
            _require_nonnegative(value, attr)
            setattr(self, attr, float(value))

        if self.meal not in ("breakfast", "lunch", "dinner", "snack"):
            raise ValueError("unsupported meal")

        _validate_date(self.date)

        if self.id is not None:
            _require_nonempty(self.id, "id")

        self.grams = float(self.grams)


@dataclass
class WeightLog:
    """Запись веса пользователя за конкретный календарный день."""

    user_id: str
    weight_kg: float
    date: str
    id: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_nonempty(self.user_id, "user_id")
        _require_positive(self.weight_kg, "weight_kg")
        _validate_date(self.date)

        if self.id is not None:
            _require_nonempty(self.id, "id")

        self.weight_kg = float(self.weight_kg)


@dataclass
class Session:
    """Сессия авторизации пользователя."""

    token: str
    user_id: str
    expires_at: datetime
    id: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_nonempty(self.token, "token")
        _require_nonempty(self.user_id, "user_id")

        if not isinstance(self.expires_at, datetime):
            raise ValueError("expires_at must be datetime")

        if self.id is not None:
            _require_nonempty(self.id, "id")
