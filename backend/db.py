"""Подключение к MongoDB и создание индексов."""
from pymongo import ASCENDING, MongoClient


def create_client(uri):
    """Создать клиент MongoDB. Подключение ленивое, до первого запроса."""
    return MongoClient(uri, serverSelectionTimeoutMS=3000)


def get_database(client, name):
    """Вернуть базу по имени."""
    return client[name]


def ensure_indexes(db):
    """Создать индексы из схемы данных. Повторный вызов безопасен."""
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.sessions.create_index([("token", ASCENDING)], unique=True)
    db.products.create_index([("name_lower", ASCENDING)])
    db.products.create_index([("owner_id", ASCENDING)])
    db.food_entries.create_index([("user_id", ASCENDING), ("date", ASCENDING)])
    db.weight_logs.create_index(
        [("user_id", ASCENDING), ("date", ASCENDING)], unique=True
    )
