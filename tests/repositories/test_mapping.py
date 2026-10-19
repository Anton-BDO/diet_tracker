"""Тесты преобразования BSON-документов и доменных моделей."""

from datetime import datetime, timezone

import pytest
from bson import ObjectId

from backend.domain.models import FoodEntry, MacroTargets, Product, User
from backend.repositories._mapping import (
    food_entry_from_document,
    food_entry_to_document,
    parse_object_id,
    product_from_document,
    product_to_document,
    user_from_document,
    user_to_document,
)


@pytest.fixture
def timestamps():
    """Общие даты для тестовых объектов."""
    now = datetime.now(timezone.utc)
    return now, now


@pytest.fixture
def user(timestamps):
    """Тестовый пользователь."""
    created_at, updated_at = timestamps
    return User(
        id=None,
        email="  PERSON@Example.com ",
        password_hash="hashed-password",
        name="Person",
        gender="female",
        age=30,
        height_cm=170,
        weight_kg=65,
        activity="moderate",
        goal="maintain",
        daily_calories=2000,
        macros=MacroTargets(
            protein=100,
            fat=70,
            carbs=250,
        ),
        created_at=created_at,
        updated_at=updated_at,
    )


@pytest.fixture
def product(timestamps):
    """Тестовый продукт."""
    created_at, _ = timestamps
    return Product(
        id=None,
        name="Oats",
        name_lower="",
        calories=380,
        protein=13,
        fat=7,
        carbs=68,
        is_custom=False,
        owner_id=None,
        created_at=created_at,
    )


@pytest.fixture
def food_entry(timestamps):
    """Тестовая запись дневника."""
    created_at, updated_at = timestamps
    return FoodEntry(
        id=None,
        user_id=str(ObjectId()),
        product_id=str(ObjectId()),
        product_name="Oats",
        grams=50,
        calories=190,
        protein=6.5,
        fat=3.5,
        carbs=34,
        meal="breakfast",
        date=created_at.date().isoformat(),
        created_at=created_at,
        updated_at=updated_at,
    )


def test_parse_object_id_accepts_object_id():
    """Существующий ObjectId возвращается без изменений."""
    value = ObjectId()

    assert parse_object_id(value) is value


@pytest.mark.parametrize(
    "value",
    [
        None,
        123,
        "",
        "invalid-object-id",
        "123456789012",
    ],
)
def test_parse_object_id_returns_none_for_invalid_values(value):
    """Некорректные идентификаторы преобразуются в None."""
    assert parse_object_id(value) is None


def test_parse_object_id_accepts_valid_string():
    """Строковый ObjectId преобразуется в ObjectId."""
    value = str(ObjectId())

    result = parse_object_id(value)

    assert isinstance(result, ObjectId)
    assert str(result) == value


def test_user_to_document_normalizes_email_and_macros(user):
    """Email нормализуется, числовые значения преобразуются в float."""
    document = user_to_document(user)

    assert document["email"] == "person@example.com"
    assert document["height_cm"] == 170.0
    assert document["weight_kg"] == 65.0
    assert document["macros"] == {
        "protein": 100.0,
        "fat": 70.0,
        "carbs": 250.0,
    }
    assert "_id" not in document


def test_user_to_document_converts_id(user):
    """Валидный ID пользователя записывается как ObjectId."""
    user.id = str(ObjectId())

    document = user_to_document(user)

    assert document["_id"] == ObjectId(user.id)


def test_user_to_document_rejects_invalid_id(user):
    """Некорректный ID пользователя вызывает ValueError."""
    user.id = "invalid-id"

    with pytest.raises(ValueError, match="user.id"):
        user_to_document(user)


def test_user_from_document_restores_model(user):
    """Документ пользователя преобразуется в доменную модель."""
    user.id = str(ObjectId())
    document = user_to_document(user)

    restored = user_from_document(document)

    assert restored.id == user.id
    assert restored.email == "person@example.com"
    assert restored.macros.protein == 100.0


def test_product_to_document_uses_casefold_when_name_lower_empty(product):
    """Если name_lower пустой, используется casefold имени."""
    product.name = "OÄTS"
    product.name_lower = ""

    document = product_to_document(product)

    assert document["name_lower"] == "oäts"
    assert document["owner_id"] is None
    assert document["is_custom"] is False


def test_product_to_document_converts_owner_and_product_ids(product):
    """ID владельца и продукта преобразуются в ObjectId."""
    product.id = str(ObjectId())
    product.owner_id = str(ObjectId())

    document = product_to_document(product)

    assert document["_id"] == ObjectId(product.id)
    assert document["owner_id"] == ObjectId(product.owner_id)


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("id", "product.id"),
        ("owner_id", "product.owner_id"),
    ],
)
def test_product_to_document_rejects_invalid_ids(
    product,
    field,
    message,
):
    """Некорректные ID продукта или владельца вызывают ValueError."""
    setattr(product, field, "invalid-id")

    with pytest.raises(ValueError, match=message):
        product_to_document(product)


def test_product_from_document_uses_defaults(product):
    """Отсутствующие необязательные поля получают значения по умолчанию."""
    document = product_to_document(product)
    document["_id"] = ObjectId()
    document.pop("name_lower")
    document.pop("is_custom")

    restored = product_from_document(document)

    assert restored.name_lower == "oats"
    assert restored.is_custom is False
    assert restored.owner_id is None


def test_product_from_document_restores_owner_id(product):
    """ObjectId владельца преобразуется в строку"""
    """для пользовательского продукта."""
    owner_id = ObjectId()

    product.is_custom = True
    product.owner_id = str(owner_id)

    document = product_to_document(product)
    document["_id"] = ObjectId()
    document["owner_id"] = owner_id
    document["is_custom"] = True

    restored = product_from_document(document)

    assert restored.owner_id == str(owner_id)
    assert restored.is_custom is True


def test_food_entry_to_document_converts_ids(food_entry):
    """Ссылочные ID записи сохраняются в виде ObjectId."""
    document = food_entry_to_document(food_entry)

    assert isinstance(document["user_id"], ObjectId)
    assert isinstance(document["product_id"], ObjectId)
    assert document["grams"] == 50.0
    assert document["calories"] == 190.0


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("user_id", "food_entry.user_id"),
        ("product_id", "food_entry.product_id"),
    ],
)
def test_food_entry_to_document_rejects_invalid_reference_ids(
    food_entry,
    field,
    message,
):
    """Некорректный ссылочный ID вызывает ValueError."""
    setattr(food_entry, field, "invalid-id")

    with pytest.raises(ValueError, match=message):
        food_entry_to_document(food_entry)


def test_food_entry_to_document_rejects_invalid_entry_id(food_entry):
    """Некорректный ID самой записи вызывает ValueError."""
    food_entry.id = "invalid-id"

    with pytest.raises(ValueError, match="food_entry.id"):
        food_entry_to_document(food_entry)


def test_food_entry_to_document_converts_entry_id(food_entry):
    """Валидный ID записи сохраняется как ObjectId."""
    food_entry.id = str(ObjectId())

    document = food_entry_to_document(food_entry)

    assert document["_id"] == ObjectId(food_entry.id)


def test_food_entry_from_document_restores_model(food_entry):
    """Документ записи преобразуется обратно в доменную модель."""
    document = food_entry_to_document(food_entry)
    document["_id"] = ObjectId()

    restored = food_entry_from_document(document)

    assert restored.id == str(document["_id"])
    assert restored.user_id == str(document["user_id"])
    assert restored.product_id == str(document["product_id"])
    assert restored.product_name == "Oats"
    assert restored.grams == 50.0
