"""Проверки валидации доменных моделей."""

from datetime import date, datetime, timezone

import pytest

from backend.domain.errors import ValidationError
from backend.domain.models import (
    FoodEntry,
    Product,
    Session,
    User,
    WeightLog,
    age_on,
)


def make_user(**overrides):
    """Создать валидного пользователя."""
    values = {
        "email": " User@Example.COM ",
        "password_hash": "hashed",
        "name": " Alex ",
        "sex": "male",
        "birth_date": "1990-01-01",
        "height_cm": 180,
        "weight_kg": 85,
        "activity": 1.55,
        "goal": "lose",
    }
    values.update(overrides)
    return User(**values)


def make_entry(**overrides):
    """Создать валидную запись дневника."""
    values = {
        "user_id": "u1",
        "product_id": "p1",
        "product_name": "Apple",
        "grams": 150,
        "kcal": 78,
        "protein": 0.5,
        "fat": 0.3,
        "carbs": 20,
        "meal": "snack",
        "date": "2026-10-07",
    }
    values.update(overrides)
    return FoodEntry(**values)


def test_user_normalizes_email_and_name():
    user = make_user()

    assert user.email == "user@example.com"
    assert user.name == "Alex"
    assert user.created_at.tzinfo is not None


def test_user_does_not_store_computed_nutrition_fields():
    user = make_user()

    assert not hasattr(user, "daily_calories")
    assert not hasattr(user, "macros")


@pytest.mark.parametrize(
    "field,value",
    [
        ("sex", "unknown"),
        ("activity", 1.3),
        ("goal", "maintain"),
        ("height_cm", 99),
        ("height_cm", 251),
        ("weight_kg", 29),
        ("weight_kg", 301),
        ("birth_date", "not-a-date"),
    ],
)
def test_user_rejects_invalid_profile_values(field, value):
    with pytest.raises(ValidationError) as error:
        make_user(**{field: value})

    assert error.value.field == field
    assert str(error.value)


def test_user_rejects_underage_profile():
    underage_birth_date = date.today().replace(
        year=date.today().year - 10
    ).isoformat()

    with pytest.raises(ValidationError) as error:
        make_user(birth_date=underage_birth_date)

    assert error.value.field == "birth_date"


def test_user_rejects_profile_over_100_years_old():
    old_birth_date = date.today().replace(
        year=date.today().year - 101
    ).isoformat()

    with pytest.raises(ValidationError) as error:
        make_user(birth_date=old_birth_date)

    assert error.value.field == "birth_date"


@pytest.mark.parametrize("height", [100, 250])
def test_user_accepts_height_boundaries(height):
    assert make_user(height_cm=height).height_cm == height


@pytest.mark.parametrize("weight", [30, 300])
def test_user_accepts_weight_boundaries(weight):
    assert make_user(weight_kg=weight).weight_kg == weight


def test_user_rejects_bad_email_with_field():
    with pytest.raises(ValidationError) as error:
        make_user(email="not-an-email")

    assert error.value.field == "email"


def test_age_on_calculates_completed_years():
    assert age_on("2000-10-21", date(2026, 10, 20)) == 25
    assert age_on("2000-10-20", date(2026, 10, 20)) == 26


@pytest.mark.parametrize(
    "factor",
    [1.2, 1.375, 1.55, 1.725, 1.9],
)
def test_user_accepts_supported_activity_factors(factor):
    assert make_user(activity=factor).activity == factor


def test_product_normalizes_name_and_uses_owner_id():
    product = Product(
        name=" Chicken Breast ",
        kcal=120,
        protein=22,
        fat=2,
        carbs=0,
        owner_id="user-1",
    )

    assert product.name == "Chicken Breast"
    assert product.name_lower == "chicken breast"
    assert product.owner_id == "user-1"
    assert not hasattr(product, "is_custom")


def test_product_without_owner_is_global():
    product = Product(
        name="Apple",
        kcal=52,
        protein=0.3,
        fat=0.2,
        carbs=14,
    )

    assert product.owner_id is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("kcal", -1),
        ("protein", float("nan")),
        ("fat", True),
    ],
)
def test_product_rejects_invalid_nutrients(field, value):
    values = {
        "name": "Apple",
        "kcal": 52,
        "protein": 0.3,
        "fat": 0.2,
        "carbs": 14,
    }
    values[field] = value

    with pytest.raises(ValidationError) as error:
        Product(**values)

    assert error.value.field == field


def test_food_entry_accepts_valid_values_and_kcal_field():
    entry = make_entry()

    assert entry.grams == 150
    assert entry.kcal == 78


@pytest.mark.parametrize(
    "grams",
    [0, 0.9, 5000.1, 6000, True],
)
def test_food_entry_validates_grams_range(grams):
    with pytest.raises(ValidationError) as error:
        make_entry(grams=grams)

    assert error.value.field == "grams"


@pytest.mark.parametrize("grams", [1, 5000])
def test_food_entry_accepts_grams_boundaries(grams):
    assert make_entry(grams=grams).grams == grams


@pytest.mark.parametrize(
    "field,value",
    [
        ("meal", "late-night"),
        ("date", "2026-02-30"),
        ("date", "07-10-2026"),
    ],
)
def test_food_entry_rejects_invalid_meal_or_date(field, value):
    with pytest.raises(ValidationError) as error:
        make_entry(**{field: value})

    assert error.value.field == field


def test_weight_log_validates_weight_range_and_date():
    log = WeightLog(
        user_id="u1",
        weight_kg=70,
        date="2026-10-07",
    )

    assert log.weight_kg == 70

    with pytest.raises(ValidationError) as error:
        WeightLog(
            user_id="u1",
            weight_kg=301,
            date="2026-10-07",
        )

    assert error.value.field == "weight_kg"


def test_session_accepts_expiration_datetime():
    expiration = datetime(2027, 1, 1, tzinfo=timezone.utc)
    session = Session(
        token="token",
        user_id="u1",
        expires_at=expiration,
    )

    assert session.expires_at == expiration


def test_session_rejects_non_datetime_expiration():
    with pytest.raises(ValidationError) as error:
        Session(
            token="token",
            user_id="u1",
            expires_at="tomorrow",
        )

    assert error.value.field == "expires_at"
