"""Тесты доменных моделей."""

from datetime import datetime, timezone

import pytest

from backend.domain.models import (
    FoodEntry,
    MacroTargets,
    Product,
    Session,
    User,
    WeightLog,
)


def test_user_normalizes_email_and_accepts_macro_dict():
    user = User(
        email=" User@Example.COM ",
        password_hash="hashed-password",
        name="Alex",
        gender="male",
        age=25,
        height_cm=180,
        weight_kg=85,
        activity="moderate",
        goal="lose",
        daily_calories=2150,
        macros={"protein": 160, "fat": 70, "carbs": 200},
    )

    assert user.email == "user@example.com"
    assert isinstance(user.macros, MacroTargets)
    assert user.macros.protein == 160.0
    assert user.created_at.tzinfo is not None


def test_user_rejects_invalid_gender():
    with pytest.raises(ValueError):
        User(
            email="alex@example.com",
            password_hash="hashed-password",
            name="Alex",
            gender="unknown",
            age=25,
            height_cm=180,
            weight_kg=85,
            activity="moderate",
            goal="lose",
            daily_calories=2150,
            macros=MacroTargets(160, 70, 200),
        )


def test_user_rejects_invalid_activity_and_goal():
    with pytest.raises(ValueError):
        User(
            email="alex@example.com",
            password_hash="hashed-password",
            name="Alex",
            gender="male",
            age=25,
            height_cm=180,
            weight_kg=85,
            activity="unknown",
            goal="lose",
            daily_calories=2150,
            macros=MacroTargets(160, 70, 200),
        )

    with pytest.raises(ValueError):
        User(
            email="alex@example.com",
            password_hash="hashed-password",
            name="Alex",
            gender="male",
            age=25,
            height_cm=180,
            weight_kg=85,
            activity="moderate",
            goal="unknown",
            daily_calories=2150,
            macros=MacroTargets(160, 70, 200),
        )


def test_macros_reject_negative_values():
    with pytest.raises(ValueError):
        MacroTargets(protein=-1, fat=70, carbs=200)


def test_product_normalizes_name():
    product = Product(
        name=" Chicken Breast ",
        calories=120,
        protein=22,
        fat=2,
        carbs=0,
    )

    assert product.name == "Chicken Breast"
    assert product.name_lower == "chicken breast"


def test_custom_product_requires_owner():
    with pytest.raises(ValueError):
        Product(
            name="My product",
            calories=100,
            protein=10,
            fat=2,
            carbs=3,
            is_custom=True,
        )


def test_system_product_cannot_have_owner():
    with pytest.raises(ValueError):
        Product(
            name="System product",
            calories=100,
            protein=10,
            fat=2,
            carbs=3,
            is_custom=False,
            owner_id="user-123",
        )


def test_product_rejects_negative_calories():
    with pytest.raises(ValueError):
        Product(
            name="Product",
            calories=-1,
            protein=10,
            fat=2,
            carbs=3,
        )


def test_food_entry_accepts_valid_date_and_meal():
    entry = FoodEntry(
        user_id="user-123",
        product_id="product-123",
        product_name="Apple",
        grams=150,
        calories=78,
        protein=0.5,
        fat=0.3,
        carbs=20,
        meal="snack",
        date="2026-10-07",
    )

    assert entry.grams == 150.0
    assert entry.date == "2026-10-07"
    assert entry.meal == "snack"


def test_food_entry_rejects_invalid_meal():
    with pytest.raises(ValueError):
        FoodEntry(
            user_id="user-123",
            product_id="product-123",
            product_name="Apple",
            grams=150,
            calories=78,
            protein=0.5,
            fat=0.3,
            carbs=20,
            meal="late-night",
            date="2026-10-07",
        )


def test_food_entry_rejects_invalid_date():
    with pytest.raises(ValueError):
        FoodEntry(
            user_id="user-123",
            product_id="product-123",
            product_name="Apple",
            grams=150,
            calories=78,
            protein=0.5,
            fat=0.3,
            carbs=20,
            meal="snack",
            date="2026-02-30",
        )


def test_weight_log_rejects_invalid_date():
    with pytest.raises(ValueError):
        WeightLog(
            user_id="user-123",
            weight_kg=70,
            date="07-10-2026",
        )


def test_weight_log_accepts_valid_data():
    log = WeightLog(
        user_id="user-123",
        weight_kg=70,
        date="2026-10-07",
    )

    assert log.weight_kg == 70.0
    assert log.date == "2026-10-07"


def test_session_accepts_datetime_expiration():
    expiration = datetime(2027, 1, 1, tzinfo=timezone.utc)

    session = Session(
        token="session-token",
        user_id="user-123",
        expires_at=expiration,
    )

    assert session.token == "session-token"
    assert session.expires_at == expiration
