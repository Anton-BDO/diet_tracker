import pytest
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from backend.db import create_client, ensure_indexes, get_database


def test_create_client_is_lazy():
    client = create_client("mongodb://localhost:27017")
    assert isinstance(client, MongoClient)
    client.close()


def test_get_database(mongo_client):
    assert get_database(mongo_client, "x").name == "x"


def test_indexes_created(db):
    ensure_indexes(db)
    assert "email_1" in db.users.index_information()
    assert "user_id_1_date_1" in db.food_entries.index_information()


def test_ensure_indexes_is_idempotent(db):
    ensure_indexes(db)
    ensure_indexes(db)


def test_email_is_unique(db):
    ensure_indexes(db)
    db.users.insert_one({"email": "a@b.ru"})
    with pytest.raises(DuplicateKeyError):
        db.users.insert_one({"email": "a@b.ru"})


def test_one_weight_per_day(db):
    ensure_indexes(db)
    db.weight_logs.insert_one({"user_id": 1, "date": "2026-10-09"})
    with pytest.raises(DuplicateKeyError):
        db.weight_logs.insert_one({"user_id": 1, "date": "2026-10-09"})
