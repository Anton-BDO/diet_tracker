"""Доменные модели diet_tracker."""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from math import isfinite
from typing import Literal, Optional

from backend.domain.errors import ValidationError


Sex = Literal["male", "female"]
Activity = Literal[1.2, 1.375, 1.55, 1.725, 1.9]
Goal = Literal["lose", "keep", "gain"]
Meal = Literal["breakfast", "lunch", "dinner", "snack"]

ACTIVITY_FACTORS = (1.2, 1.375, 1.55, 1.725, 1.9)


def utc_now() -> datetime:
    """Вернуть текущее время в UTC."""
    return datetime.now(timezone.utc)


def _require_nonempty(value: str, field_name: str) -> None:
    """Проверить, что значение — непустая строка."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(
            "Поле должно быть непустой строкой",
            field_name,
        )


def _require_number(value: float, field_name: str) -> float:
    """Проверить, что значение — конечное число, но не bool."""
    invalid_type = isinstance(value, bool) or not isinstance(
        value, (int, float)
    )
    if invalid_type or not isfinite(value):
        raise ValidationError(
            "Значение должно быть конечным числом",
            field_name,
        )
    return float(value)


def _require_range(
    value: float,
    field_name: str,
    minimum: float,
    maximum: float,
) -> float:
    """Проверить числовое значение и его диапазон."""
    number = _require_number(value, field_name)
    if not minimum <= number <= maximum:
        raise ValidationError(
            f"Значение должно быть в диапазоне "
            f"{minimum:g}–{maximum:g}",
            field_name,
        )
    return number


def _require_nonnegative(value: float, field_name: str) -> float:
    """Проверить, что число неотрицательное."""
    number = _require_number(value, field_name)
    if number < 0:
        raise ValidationError(
            "Значение не может быть отрицательным",
            field_name,
        )
    return number


def _validate_date(value: str, field_name: str = "date") -> date:
    """Проверить дату в формате YYYY-MM-DD."""
    _require_nonempty(value, field_name)

    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValidationError(
            "Дата должна быть в формате ГГГГ-ММ-ДД",
            field_name,
        ) from None

    if parsed.isoformat() != value:
        raise ValidationError(
            "Дата должна быть в формате ГГГГ-ММ-ДД",
            field_name,
        )

    return parsed


def age_on(birth_date: str, today: Optional[date] = None) -> int:
    """Рассчитать полный возраст на указанную дату."""
    born = _validate_date(birth_date, "birth_date")
    current = today or date.today()

    if born > current:
        raise ValidationError(
            "Дата рождения не может быть в будущем",
            "birth_date",
        )

    birthday_not_reached = (
        (current.month, current.day) < (born.month, born.day)
    )
    return current.year - born.year - birthday_not_reached


def _validate_age(birth_date: str) -> None:
    """Проверить, что возраст пользователя — от 14 до 100 лет."""
    age = age_on(birth_date)
    if not 14 <= age <= 100:
        raise ValidationError(
            "Возраст должен быть от 14 до 100 лет",
            "birth_date",
        )


def _validate_activity(value: float) -> None:
    """Проверить коэффициент физической активности."""
    invalid_type = isinstance(value, bool) or not isinstance(
        value, (int, float)
    )
    if (
        invalid_type
        or not isfinite(value)
        or value not in ACTIVITY_FACTORS
    ):
        raise ValidationError(
            "Активность должна быть одним из значений: "
            "1.2, 1.375, 1.55, 1.725, 1.9",
            "activity",
        )


@dataclass
class User:
    """Учётные данные и параметры профиля пользователя."""

    email: str
    password_hash: str
    name: str
    sex: Sex
    birth_date: str
    height_cm: float
    weight_kg: float
    activity: float
    goal: Goal
    id: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self._validate_identity()
        self._validate_profile()

        if self.id is not None:
            _require_nonempty(self.id, "id")

    def _validate_identity(self) -> None:
        """Проверить и нормализовать данные учётной записи."""
        _require_nonempty(self.email, "email")
        _require_nonempty(self.password_hash, "password_hash")
        _require_nonempty(self.name, "name")

        self.email = self.email.strip().lower()
        self.name = self.name.strip()

        if "@" not in self.email or self.email.startswith("@"):
            raise ValidationError(
                "Укажите корректный email",
                "email",
            )

    def _validate_profile(self) -> None:
        """Проверить параметры профиля пользователя."""
        if self.sex not in ("male", "female"):
            raise ValidationError(
                "Пол должен быть male или female",
                "sex",
            )

        _validate_age(self.birth_date)

        self.height_cm = _require_range(
            self.height_cm,
            "height_cm",
            100,
            250,
        )
        self.weight_kg = _require_range(
            self.weight_kg,
            "weight_kg",
            30,
            300,
        )

        _validate_activity(self.activity)

        if self.goal not in ("lose", "keep", "gain"):
            raise ValidationError(
                "Цель должна быть lose, keep или gain",
                "goal",
            )


@dataclass
class Product:
    """Общий продукт или продукт пользователя."""

    name: str
    kcal: float
    protein: float
    fat: float
    carbs: float
    owner_id: Optional[str] = None
    id: Optional[str] = None
    name_lower: str = ""
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_nonempty(self.name, "name")
        self.name = self.name.strip()
        self.name_lower = self.name.casefold()

        for attr in ("kcal", "protein", "fat", "carbs"):
            value = getattr(self, attr)
            setattr(
                self,
                attr,
                _require_nonnegative(value, attr),
            )

        if self.owner_id is not None:
            _require_nonempty(self.owner_id, "owner_id")

        if self.id is not None:
            _require_nonempty(self.id, "id")


@dataclass
class FoodEntry:
    """Снимок нутриентов продукта для порции в дневнике."""

    user_id: str
    product_id: str
    product_name: str
    grams: float
    kcal: float
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

        self.grams = _require_range(
            self.grams,
            "grams",
            1,
            5000,
        )

        for attr in ("kcal", "protein", "fat", "carbs"):
            value = getattr(self, attr)
            setattr(
                self,
                attr,
                _require_nonnegative(value, attr),
            )

        if self.meal not in (
            "breakfast",
            "lunch",
            "dinner",
            "snack",
        ):
            raise ValidationError(
                "Недопустимый тип приёма пищи",
                "meal",
            )

        _validate_date(self.date)

        if self.id is not None:
            _require_nonempty(self.id, "id")


@dataclass
class WeightLog:
    """Измерение веса пользователя за календарный день."""

    user_id: str
    weight_kg: float
    date: str
    id: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_nonempty(self.user_id, "user_id")

        self.weight_kg = _require_range(
            self.weight_kg,
            "weight_kg",
            30,
            300,
        )

        _validate_date(self.date)

        if self.id is not None:
            _require_nonempty(self.id, "id")


@dataclass
class Session:
    """Сессия авторизации со сроком действия."""

    token: str
    user_id: str
    expires_at: datetime
    id: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        _require_nonempty(self.token, "token")
        _require_nonempty(self.user_id, "user_id")

        if not isinstance(self.expires_at, datetime):
            raise ValidationError(
                "Срок действия должен быть датой и временем",
                "expires_at",
            )

        if self.id is not None:
            _require_nonempty(self.id, "id")
