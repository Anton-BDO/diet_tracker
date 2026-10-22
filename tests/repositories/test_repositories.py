"""Интеграционные тесты репозиториев на mongomock."""

import pytest
from bson import ObjectId

from backend.domain.models import FoodEntry, Product, User
from backend.repositories import (
    FoodEntryRepository,
    ProductRepository,
    UserRepository,
)


def make_user(email="person@example.com"):
    """Создать валидную доменную модель пользователя."""
    return User(
        email=email,
        password_hash="hashed-password",
        name="Person",
        sex="female",
        birth_date="1996-01-01",
        height_cm=165,
        weight_kg=60,
        activity=1.55,
        goal="keep",
    )


def make_product(name="Oats", owner_id=None):
    """Создать валидную доменную модель продукта."""
    return Product(
        name=name,
        kcal=380,
        protein=13,
        fat=7,
        carbs=68,
        owner_id=owner_id,
    )


def make_entry(user_id, product_id, date="2026-10-18"):
    """Создать валидную доменную модель записи дневника."""
    return FoodEntry(
        user_id=user_id,
        product_id=product_id,
        product_name="Oats",
        grams=50,
        kcal=190,
        protein=6.5,
        fat=3.5,
        carbs=34,
        meal="breakfast",
        date=date,
    )


# ============================================================================
# UserRepository
# ============================================================================


def test_user_create_and_read_by_id_and_email(db):
    repository = UserRepository(db)

    user = repository.create(make_user("PERSON@Example.com"))

    assert ObjectId.is_valid(user.id)

    stored = db.users.find_one({"_id": ObjectId(user.id)})

    assert stored["email"] == "person@example.com"
    assert stored["sex"] == "female"
    assert stored["birth_date"] == "1996-01-01"
    assert stored["activity"] == 1.55
    assert stored["goal"] == "keep"

    # В MongoDB должна сохраняться актуальная схема пользователя.
    assert not {
        "gender",
        "age",
        "daily_calories",
        "macros",
    }.intersection(stored)

    loaded_by_id = repository.get_by_id(user.id)
    loaded_by_email = repository.get_by_email("PERSON@example.COM")

    assert loaded_by_id is not None
    assert loaded_by_id.id == user.id
    assert loaded_by_id.email == "person@example.com"

    assert loaded_by_email is not None
    assert loaded_by_email.id == user.id

    assert repository.get_by_id("invalid-id") is None
    assert repository.get_by_id(str(ObjectId())) is None
    assert repository.get_by_email(" ") is None
    assert repository.get_by_email("missing@example.com") is None


def test_user_create_does_not_persist_temporary_id(db):
    repository = UserRepository(db)

    user = repository.create(make_user())
    stored = db.users.find_one({"_id": ObjectId(user.id)})

    assert "id" not in stored
    assert "_id" in stored


def test_user_update_replaces_document(db):
    repository = UserRepository(db)
    user = repository.create(make_user())

    user.name = "Updated Name"
    user.weight_kg = 62

    result = repository.update(user)

    assert result is user

    stored_user = repository.get_by_id(user.id)

    assert stored_user is not None
    assert stored_user.name == "Updated Name"
    assert stored_user.weight_kg == 62

    assert stored_user.updated_at is not None
    assert user.updated_at is not None


def test_user_update_returns_none_for_invalid_or_missing_id(db):
    repository = UserRepository(db)

    user_without_id = make_user()

    assert repository.update(user_without_id) is None

    user_without_document = make_user()
    user_without_document.id = str(ObjectId())

    assert repository.update(user_without_document) is None


def test_user_repository_rejects_wrong_model_type(db):
    repository = UserRepository(db)

    with pytest.raises(TypeError):
        repository.create({"email": "person@example.com"})

    with pytest.raises(TypeError):
        repository.update({"id": str(ObjectId())})


# ============================================================================
# ProductRepository
# ============================================================================


def test_product_create_converts_owner_id_and_uses_current_schema(db):
    repository = ProductRepository(db)
    owner_id = str(ObjectId())

    product = repository.create(make_product(owner_id=owner_id))

    stored = db.products.find_one({"_id": ObjectId(product.id)})

    assert stored["owner_id"] == ObjectId(owner_id)
    assert product.id == str(stored["_id"])

    assert stored["kcal"] == 380
    assert "calories" not in stored
    assert "is_custom" not in stored

    loaded = repository.get_by_id(product.id, owner_id)

    assert loaded is not None
    assert loaded.owner_id == owner_id
    assert loaded.kcal == 380


def test_product_search_respects_product_visibility_and_case(db):
    repository = ProductRepository(db)

    owner_a = str(ObjectId())
    owner_b = str(ObjectId())

    repository.create(make_product("Oatmeal"))
    repository.create(make_product("Oat drink", owner_id=owner_a))
    repository.create(make_product("Oat bar", owner_id=owner_b))
    repository.create(make_product("Apple", owner_id=owner_a))

    results = repository.search("OAT", owner_a)

    assert {item.name for item in results} == {
        "Oatmeal",
        "Oat drink",
    }


def test_product_search_with_empty_query_returns_visible_products(db):
    repository = ProductRepository(db)
    owner_id = str(ObjectId())

    repository.create(make_product("Oats"))
    repository.create(make_product("Apple", owner_id=owner_id))
    repository.create(
        make_product("Private product", owner_id=str(ObjectId()))
    )

    results = repository.search("", owner_id)

    assert {item.name for item in results} == {"Oats", "Apple"}


def test_product_search_rejects_invalid_user_id(db):
    repository = ProductRepository(db)

    with pytest.raises(ValueError):
        repository.search("oat", "not-an-object-id")


def test_product_create_rejects_invalid_owner_id(db):
    repository = ProductRepository(db)

    with pytest.raises(ValueError):
        repository.create(make_product(owner_id="not-an-object-id"))


def test_product_get_by_id_hides_another_users_product(db):
    repository = ProductRepository(db)

    owner_a = str(ObjectId())
    owner_b = str(ObjectId())

    private_product = repository.create(
        make_product("Private oats", owner_id=owner_b)
    )
    system_product = repository.create(make_product("System oats"))

    assert repository.get_by_id(private_product.id, owner_a) is None
    assert repository.get_by_id(private_product.id, owner_b) is not None
    assert repository.get_by_id(system_product.id, owner_a) is not None
    assert repository.get_by_id("invalid-id", owner_a) is None


def test_product_repository_rejects_wrong_model_type(db):
    repository = ProductRepository(db)

    with pytest.raises(TypeError):
        repository.create({"name": "Oats"})


# ============================================================================
# FoodEntryRepository
# ============================================================================


def test_food_entry_create_converts_reference_ids_and_uses_current_schema(
    db,
):
    repository = FoodEntryRepository(db)

    user_id = ObjectId()
    product_id = ObjectId()

    entry = repository.create(
        make_entry(str(user_id), str(product_id))
    )

    stored = db.food_entries.find_one({"_id": ObjectId(entry.id)})

    assert stored["user_id"] == user_id
    assert stored["product_id"] == product_id
    assert stored["product_name"] == "Oats"

    assert stored["kcal"] == 190
    assert "calories" not in stored


def test_food_entry_read_filters_by_user_and_date(db):
    repository = FoodEntryRepository(db)

    user_id = str(ObjectId())
    product_id = str(ObjectId())

    entry = repository.create(
        make_entry(user_id, product_id, "2026-10-18")
    )
    repository.create(
        make_entry(user_id, product_id, "2026-10-17")
    )
    repository.create(
        make_entry(str(ObjectId()), product_id, "2026-10-18")
    )

    results = repository.get_by_user_and_date(
        user_id,
        "2026-10-18",
    )

    assert len(results) == 1
    assert results[0].id == entry.id
    assert results[0].user_id == user_id
    assert results[0].product_id == product_id


def test_food_entry_rejects_invalid_ids(db):
    repository = FoodEntryRepository(db)

    with pytest.raises(ValueError):
        repository.get_by_user_and_date(
            "invalid-id",
            "2026-10-18",
        )

    with pytest.raises(ValueError):
        repository.create(
            make_entry("invalid-id", str(ObjectId()))
        )

    with pytest.raises(ValueError):
        repository.create(
            make_entry(str(ObjectId()), "invalid-id")
        )


def test_food_entry_delete_requires_owner(db):
    repository = FoodEntryRepository(db)

    owner_id = str(ObjectId())
    another_user_id = str(ObjectId())

    entry = repository.create(
        make_entry(owner_id, str(ObjectId()))
    )

    # Другой пользователь не может удалить эту запись.
    assert repository.delete(entry.id, another_user_id) is False

    # После неудачной попытки запись остаётся в базе.
    stored = db.food_entries.find_one({"_id": ObjectId(entry.id)})
    assert stored is not None

    # Владелец может удалить запись.
    assert repository.delete(entry.id, owner_id) is True

    stored = db.food_entries.find_one({"_id": ObjectId(entry.id)})
    assert stored is None

    # Повторное удаление и некорректный идентификатор неуспешны.
    assert repository.delete(entry.id, owner_id) is False
    assert repository.delete("invalid-id", owner_id) is False


def test_food_entry_update_changes_grams_and_meal_for_owner(db):
    repository = FoodEntryRepository(db)

    user_id = str(ObjectId())

    entry = repository.create(
        make_entry(user_id, str(ObjectId()))
    )

    entry.grams = 100
    entry.meal = "lunch"

    result = repository.update(entry, user_id)

    assert result is entry

    stored = db.food_entries.find_one({"_id": ObjectId(entry.id)})

    assert stored["grams"] == 100
    assert stored["meal"] == "lunch"

    # Репозиторий обновляет только поля PATCH.
    # Пересчёт КБЖУ при изменении граммов выполняется сервисом.
    assert stored["kcal"] == 190
    assert stored["protein"] == 6.5
    assert stored["fat"] == 3.5
    assert stored["carbs"] == 34

    # MongoDB хранит даты с точностью до миллисекунд.
    assert result.updated_at is not None
    assert stored["updated_at"] is not None
    assert (
        result.updated_at.replace(tzinfo=None).replace(microsecond=0)
        == stored["updated_at"].replace(microsecond=0)
    )


def test_food_entry_update_does_not_modify_another_users_entry(db):
    repository = FoodEntryRepository(db)

    owner_id = str(ObjectId())
    another_user_id = str(ObjectId())

    entry = repository.create(
        make_entry(owner_id, str(ObjectId()))
    )

    entry.grams = 100
    entry.meal = "lunch"

    # Чужая запись не должна обновляться.
    assert repository.update(entry, another_user_id) is None

    stored = db.food_entries.find_one({"_id": ObjectId(entry.id)})

    assert stored["grams"] == 50
    assert stored["meal"] == "breakfast"


def test_food_entry_update_returns_none_for_missing_entry(db):
    repository = FoodEntryRepository(db)

    user_id = str(ObjectId())

    entry = make_entry(user_id, str(ObjectId()))
    entry.id = str(ObjectId())

    assert repository.update(entry, user_id) is None


def test_food_entry_repository_rejects_wrong_model_type(db):
    repository = FoodEntryRepository(db)

    with pytest.raises(TypeError):
        repository.create({"user_id": str(ObjectId())})

    with pytest.raises(TypeError):
        repository.update(
            {"id": str(ObjectId())},
            str(ObjectId()),
        )


# ============================================================================
# Проверка отсутствия альтернативных имён методов
# ============================================================================


def test_repositories_have_one_canonical_method_name_per_operation():
    # UserRepository
    assert not hasattr(UserRepository, "find_by_id")
    assert not hasattr(UserRepository, "find_by_email")
    assert not hasattr(UserRepository, "save")

    # ProductRepository
    assert not hasattr(ProductRepository, "find")
    assert not hasattr(ProductRepository, "find_by_name")
    assert not hasattr(ProductRepository, "search_visible")
    assert not hasattr(ProductRepository, "save")

    # FoodEntryRepository
    assert not hasattr(FoodEntryRepository, "find_by_user_and_date")
    assert not hasattr(FoodEntryRepository, "get_for_day")
    assert not hasattr(FoodEntryRepository, "save")
