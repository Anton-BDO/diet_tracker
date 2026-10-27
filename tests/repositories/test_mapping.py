"""Тесты преобразования BSON-документов и доменных моделей."""

from datetime import datetime, timezone

import pytest
from bson import ObjectId

from backend.domain.models import FoodEntry, Product, Session, User
from backend.repositories._mapping import (
    food_entry_from_document,
    food_entry_to_document,
    parse_object_id,
    product_from_document,
    product_to_document,
    user_from_document,
    user_to_document,
    session_from_document,
    session_to_document,
)


@pytest.fixture
def timestamps():
    """Общие даты для тестовых объектов."""
    now = datetime.now(timezone.utc)
    return now, now


@pytest.fixture
def user(timestamps):
    """Пользователь с полями, соответствующими архитектуре проекта."""
    created_at, updated_at = timestamps

    return User(
        id=None,
        email="  PERSON@Example.com ",
        password_hash="hashed-password",
        name="Person",
        sex="female",
        birth_date="1996-01-01",
        height_cm=170,
        weight_kg=65,
        activity=1.55,
        goal="keep",
        created_at=created_at,
        updated_at=updated_at,
    )


@pytest.fixture
def product(timestamps):
    """Продукт с полями актуальной схемы MongoDB."""
    created_at, _ = timestamps

    return Product(
        id=None,
        name="Oats",
        name_lower="",
        kcal=380,
        protein=13,
        fat=7,
        carbs=68,
        owner_id=None,
        created_at=created_at,
    )


@pytest.fixture
def food_entry(timestamps):
    """Запись дневника с полями актуальной схемы MongoDB."""
    created_at, updated_at = timestamps

    return FoodEntry(
        id=None,
        user_id=str(ObjectId()),
        product_id=str(ObjectId()),
        product_name="Oats",
        grams=50,
        kcal=190,
        protein=6.5,
        fat=3.5,
        carbs=34,
        meal="breakfast",
        date=created_at.date().isoformat(),
        created_at=created_at,
        updated_at=updated_at,
    )


# ============================================================================
# Преобразование идентификаторов
# ============================================================================


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
    """Строковый ObjectId преобразуется в BSON ObjectId."""
    value = str(ObjectId())

    result = parse_object_id(value)

    assert isinstance(result, ObjectId)
    assert str(result) == value


# ============================================================================
# Преобразование пользователей
# ============================================================================


def test_user_to_document_normalizes_email_and_maps_architecture_fields(user):
    """Пользователь сериализуется по актуальной схеме без вычисляемых полей."""
    document = user_to_document(user)

    assert document["email"] == "person@example.com"
    assert document["sex"] == "female"
    assert document["birth_date"] == "1996-01-01"
    assert document["activity"] == 1.55
    assert document["goal"] == "keep"
    assert document["height_cm"] == 170.0
    assert document["weight_kg"] == 65.0

    assert "_id" not in document

    assert {"sex", "birth_date", "activity", "goal"} <= document.keys()


def test_user_to_document_converts_id(user):
    """Валидный строковый ID пользователя сохраняется как ObjectId."""
    user.id = str(ObjectId())

    document = user_to_document(user)

    assert document["_id"] == ObjectId(user.id)


def test_user_to_document_rejects_invalid_id(user):
    """Некорректный ID пользователя приводит к ValueError."""
    user.id = "invalid-id"

    with pytest.raises(ValueError, match="user.id"):
        user_to_document(user)


def test_user_from_document_restores_model(user):
    """Документ пользователя восстанавливается в доменную модель."""
    user.id = str(ObjectId())
    document = user_to_document(user)

    restored = user_from_document(document)

    assert restored.id == user.id
    assert restored.email == "person@example.com"
    assert restored.password_hash == "hashed-password"
    assert restored.name == "Person"
    assert restored.sex == "female"
    assert restored.birth_date == "1996-01-01"
    assert restored.height_cm == 170.0
    assert restored.weight_kg == 65.0
    assert restored.activity == 1.55
    assert restored.goal == "keep"


# ============================================================================
# Преобразование продуктов
# ============================================================================


def test_product_to_document_uses_casefold_when_name_lower_empty(product):
    """При пустом name_lower значение формируется через casefold()."""
    product.name = "OÄTS"
    product.name_lower = ""

    document = product_to_document(product)

    assert document["name_lower"] == "oäts"
    assert document["owner_id"] is None
    assert document["kcal"] == 380.0
    assert document["protein"] == 13.0
    assert document["fat"] == 7.0
    assert document["carbs"] == 68.0

    assert "calories" not in document


def test_product_to_document_converts_owner_and_product_ids(product):
    """ID продукта и владельца сохраняются в MongoDB как ObjectId."""
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
def test_product_to_document_rejects_invalid_ids(product, field, message):
    """Некорректный ID продукта или владельца приводит к ValueError."""
    setattr(product, field, "invalid-id")

    with pytest.raises(ValueError, match=message):
        product_to_document(product)


def test_product_from_document_uses_defaults(product):
    """При отсутствии name_lower используется имя, owner_id остаётся None."""
    document = product_to_document(product)
    document["_id"] = ObjectId()
    document.pop("name_lower")

    restored = product_from_document(document)

    assert restored.name_lower == "oats"
    assert restored.owner_id is None
    assert restored.kcal == 380.0
    assert restored.protein == 13.0
    assert restored.fat == 7.0
    assert restored.carbs == 68.0


def test_product_from_document_restores_owner_id(product):
    """ObjectId владельца преобразуется обратно в строку."""
    owner_id = ObjectId()
    product.owner_id = str(owner_id)

    document = product_to_document(product)
    document["_id"] = ObjectId()

    restored = product_from_document(document)

    assert restored.owner_id == str(owner_id)


# ============================================================================
# Преобразование записей дневника
# ============================================================================


def test_food_entry_to_document_converts_ids_and_uses_kcal(food_entry):
    """Ссылочные ID становятся ObjectId, нутриенты хранятся в поле kcal."""
    document = food_entry_to_document(food_entry)

    assert isinstance(document["user_id"], ObjectId)
    assert isinstance(document["product_id"], ObjectId)

    assert document["product_name"] == "Oats"
    assert document["grams"] == 50.0
    assert document["kcal"] == 190.0
    assert document["protein"] == 6.5
    assert document["fat"] == 3.5
    assert document["carbs"] == 34.0
    assert document["meal"] == "breakfast"

    assert "calories" not in document


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
    """Некорректный ссылочный ID приводит к ValueError."""
    setattr(food_entry, field, "invalid-id")

    with pytest.raises(ValueError, match=message):
        food_entry_to_document(food_entry)


def test_food_entry_to_document_rejects_invalid_entry_id(food_entry):
    """Некорректный ID записи приводит к ValueError."""
    food_entry.id = "invalid-id"

    with pytest.raises(ValueError, match="food_entry.id"):
        food_entry_to_document(food_entry)


def test_food_entry_to_document_converts_entry_id(food_entry):
    """Валидный ID записи сохраняется как ObjectId."""
    food_entry.id = str(ObjectId())

    document = food_entry_to_document(food_entry)

    assert document["_id"] == ObjectId(food_entry.id)


def test_food_entry_from_document_restores_model(food_entry):
    """Документ записи дневника восстанавливается в доменную модель."""
    document = food_entry_to_document(food_entry)
    document["_id"] = ObjectId()

    restored = food_entry_from_document(document)

    assert restored.id == str(document["_id"])
    assert restored.user_id == str(document["user_id"])
    assert restored.product_id == str(document["product_id"])
    assert restored.product_name == "Oats"
    assert restored.grams == 50.0
    assert restored.kcal == 190.0
    assert restored.protein == 6.5
    assert restored.fat == 3.5
    assert restored.carbs == 34.0
    assert restored.meal == "breakfast"
    assert restored.date == food_entry.date


# ============================================================================
# Преобразование сессий
# ============================================================================

def test_session_to_document_converts_user_id():
    user_id = str(ObjectId())
    session = Session(
        token="opaque-token",
        user_id=user_id,
        expires_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
    )

    document = session_to_document(session)

    assert document["token"] == "opaque-token"
    assert document["user_id"] == ObjectId(user_id)
    assert document["expires_at"] == session.expires_at
    assert "_id" not in document


def test_session_from_document_restores_model():
    session = Session(
        token="opaque-token",
        user_id=str(ObjectId()),
        expires_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
    )
    document = session_to_document(session)
    document["_id"] = ObjectId()

    restored = session_from_document(document)

    assert restored.id == str(document["_id"])
    assert restored.token == session.token
    assert restored.user_id == session.user_id
    assert restored.expires_at == session.expires_at
