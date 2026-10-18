"""Тесты подключения к MongoDB и создания индексов."""

import pytest
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from backend.db import create_client, ensure_indexes, get_database


def test_create_client_is_lazy():
    client = create_client("mongodb://localhost:27017")

    assert isinstance(client, MongoClient)

    client.close()


def test_get_database(mongo_client):
    db = get_database(mongo_client, "x")

    assert db.name == "x"


def test_indexes_created(db):
    ensure_indexes(db)

    assert "email_1" in db.users.index_information()
    assert "token_1" in db.sessions.index_information()
    assert "name_lower_1" in db.products.index_information()
    assert "owner_id_1" in db.products.index_information()
    assert "owner_id_1_name_lower_1" in (
        db.products.index_information()
    )
    assert "user_id_1_date_1" in (
        db.food_entries.index_information()
    )
    assert "user_id_1_date_1" in (
        db.weight_logs.index_information()
    )


def test_unique_indexes_created(db):
    ensure_indexes(db)

    user_indexes = db.users.index_information()
    session_indexes = db.sessions.index_information()
    weight_indexes = db.weight_logs.index_information()

    assert user_indexes["email_1"]["unique"] is True
    assert session_indexes["token_1"]["unique"] is True
    assert weight_indexes["user_id_1_date_1"]["unique"] is True


def test_ensure_indexes_is_idempotent(db):
    ensure_indexes(db)
    ensure_indexes(db)


def test_email_is_unique(db):
    ensure_indexes(db)

    db.users.insert_one({"email": "a@example.com"})

    with pytest.raises(DuplicateKeyError):
        db.users.insert_one({"email": "a@example.com"})


def test_session_token_is_unique(db):
    ensure_indexes(db)

    db.sessions.insert_one({"token": "token-123"})

    with pytest.raises(DuplicateKeyError):
        db.sessions.insert_one({"token": "token-123"})


def test_one_weight_per_user_per_day(db):
    ensure_indexes(db)

    db.weight_logs.insert_one(
        {"user_id": 1, "date": "2026-10-09"}
    )

    with pytest.raises(DuplicateKeyError):
        db.weight_logs.insert_one(
            {"user_id": 1, "date": "2026-10-09"}
        )


def test_different_users_can_log_weight_on_same_day(db):
    ensure_indexes(db)

    db.weight_logs.insert_one(
        {"user_id": 1, "date": "2026-10-09"}
    )
    db.weight_logs.insert_one(
        {"user_id": 2, "date": "2026-10-09"}
    )

    assert db.weight_logs.count_documents({}) == 2
