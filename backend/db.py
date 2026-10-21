"""Подключение к MongoDB и создание индексов."""

from pymongo import ASCENDING, MongoClient


def create_client(uri):
    """Создать клиент MongoDB с ленивым подключением."""
    return MongoClient(uri, serverSelectionTimeoutMS=3000)


def get_database(client, name):
    """Вернуть базу данных по имени."""
    return client[name]


def ensure_indexes(db):
    """Создать необходимые индексы; повторный вызов безопасен."""
    db.users.create_index(
        [("email", ASCENDING)],
        unique=True,
        name="email_1",
    )

    db.sessions.create_index(
        [("token", ASCENDING)],
        unique=True,
        name="token_1",
    )

    db.products.create_index(
        [("name_lower", ASCENDING)],
        name="name_lower_1",
    )

    db.products.create_index(
        [("owner_id", ASCENDING)],
        name="owner_id_1",
    )

    db.food_entries.create_index(
        [
            ("user_id", ASCENDING),
            ("date", ASCENDING),
        ],
        name="user_id_1_date_1",
    )

    db.weight_logs.create_index(
        [
            ("user_id", ASCENDING),
            ("date", ASCENDING),
        ],
        unique=True,
        name="user_id_1_date_1",
    )
