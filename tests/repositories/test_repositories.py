"""Тесты репозиториев и преобразования BSON."""

import pytest
from bson import ObjectId

from backend.domain.models import FoodEntry, MacroTargets, Product, User
from backend.repositories import (
    FoodEntryRepository,
    ProductRepository,
    UserRepository,
)


def make_user(email="person@example.com"):
    return User(
        email=email,
        password_hash="hashed-password",
        name="Person",
        gender="female",
        age=30,
        height_cm=165,
        weight_kg=60,
        activity="moderate",
        goal="maintain",
        daily_calories=2000,
        macros=MacroTargets(
            protein=100,
            fat=60,
            carbs=250,
        ),
    )


def make_product(name="Oats", owner_id=None):
    return Product(
        name=name,
        calories=380,
        protein=13,
        fat=7,
        carbs=68,
        is_custom=owner_id is not None,
        owner_id=owner_id,
    )


def make_entry(user_id, product_id, date="2026-10-18"):
    return FoodEntry(
        user_id=user_id,
        product_id=product_id,
        product_name="Oats",
        grams=50,
        calories=190,
        protein=6.5,
        fat=3.5,
        carbs=34,
        meal="breakfast",
        date=date,
    )


def test_user_create_and_read_by_id_and_email(db):
    repository = UserRepository(db)
    user = repository.create(make_user("PERSON@Example.com"))

    assert ObjectId.is_valid(user.id)

    stored = db.users.find_one({"_id": ObjectId(user.id)})
    assert stored["email"] == "person@example.com"

    assert repository.get_by_id(user.id).email == "person@example.com"
    assert repository.get_by_email("PERSON@example.COM").id == user.id

    assert repository.get_by_id("invalid-id") is None
    assert repository.get_by_email(" ") is None


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

    result = repository.update(user)

    assert result is user
    assert repository.get_by_id(user.id).name == "Updated Name"


def test_user_update_rejects_invalid_or_missing_id(db):
    repository = UserRepository(db)
    user = make_user()

    with pytest.raises(ValueError):
        repository.update(user)

    user.id = str(ObjectId())
    assert repository.update(user) is None


def test_product_create_converts_owner_id(db):
    repository = ProductRepository(db)
    owner_id = str(ObjectId())

    product = repository.create(make_product(owner_id=owner_id))
    stored = db.products.find_one({"_id": ObjectId(product.id)})

    assert stored["owner_id"] == ObjectId(owner_id)
    assert product.id == str(stored["_id"])
    assert repository.get_by_id(product.id, owner_id).owner_id == owner_id


def test_product_search_respects_product_visibility(db):
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


def test_product_search_with_empty_query(db):
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
    product = make_product(owner_id="not-an-object-id")

    with pytest.raises(ValueError):
        repository.create(product)


def test_product_get_by_id_hides_another_users_product(db):
    repository = ProductRepository(db)
    owner_a = str(ObjectId())
    owner_b = str(ObjectId())

    product = repository.create(
        make_product("Private oats", owner_id=owner_b)
    )

    assert repository.get_by_id(product.id, owner_a) is None
    assert repository.get_by_id(product.id, owner_b) is not None


def test_food_entry_create_converts_reference_ids(db):
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


def test_food_entry_delete(db):
    repository = FoodEntryRepository(db)
    entry = repository.create(
        make_entry(str(ObjectId()), str(ObjectId()))
    )

    assert repository.delete(entry.id) is True
    assert repository.delete(entry.id) is False
    assert repository.delete("invalid-id") is False
