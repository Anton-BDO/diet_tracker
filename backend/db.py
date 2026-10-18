"""Подключение к MongoDB и создание индексов."""
from pymongo import ASCENDING, MongoClient


def create_client(uri):
    """Создать клиент MongoDB. Подключение ленивое, до первого запроса."""
    return MongoClient(uri, serverSelectionTimeoutMS=3000)


def get_database(client, name):
    """Вернуть базу по имени."""
    return client[name]


def ensure_indexes(db):
    """Создать индексы, необходимые для работы приложения.

    Функцию можно безопасно вызывать повторно.
    """
    # У каждого пользователя должен быть уникальный email.
    db.users.create_index(
        [("email", ASCENDING)],
        unique=True,
        name="email_1",
    )

    # Токен сессии должен быть уникальным.
    db.sessions.create_index(
        [("token", ASCENDING)],
        unique=True,
        name="token_1",
    )

    # Поиск продуктов по нормализованному имени.
    db.products.create_index(
        [("name_lower", ASCENDING)],
        name="name_lower_1",
    )

    # Фильтрация пользовательских продуктов по владельцу.
    db.products.create_index(
        [("owner_id", ASCENDING)],
        name="owner_id_1",
    )

    # Поиск продуктов владельца по имени.
    db.products.create_index(
        [
            ("owner_id", ASCENDING),
            ("name_lower", ASCENDING),
        ],
        name="owner_id_1_name_lower_1",
    )

    # Выборка всех записей дневника пользователя за день.
    db.food_entries.create_index(
        [
            ("user_id", ASCENDING),
            ("date", ASCENDING),
        ],
        name="user_id_1_date_1",
    )

    # Не более одной записи веса пользователя за день.
    db.weight_logs.create_index(
        [
            ("user_id", ASCENDING),
            ("date", ASCENDING),
        ],
        unique=True,
        name="user_id_1_date_1",
    )
