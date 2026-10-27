"""Репозиторий пользователей."""

from datetime import datetime, timezone

from backend.domain.models import User
from backend.repositories._mapping import (
    parse_object_id,
    user_from_document,
    user_to_document,
)


class UserRepository:
    """Сохраняет и загружает dataclass пользователей."""

    def __init__(self, database):
        """Инициализировать репозиторий пользователей."""
        self._collection = database["users"]

    def create(self, user: User) -> User:
        """Создать пользователя и вернуть его с назначенным id."""
        if not isinstance(user, User):
            raise TypeError("user must be a User dataclass")

        document = user_to_document(user)
        document.pop("_id", None)

        result = self._collection.insert_one(document)
        user.id = str(result.inserted_id)

        return user

    def get_by_id(self, user_id: str) -> User | None:
        """Найти пользователя по строковому идентификатору."""
        object_id = parse_object_id(user_id)

        if object_id is None:
            return None

        document = self._collection.find_one({"_id": object_id})

        if document is None:
            return None

        return user_from_document(document)

    def get_by_email(self, email: str) -> User | None:
        """Найти пользователя по email без учёта регистра."""
        if not isinstance(email, str) or not email.strip():
            return None

        normalized_email = email.strip().lower()
        document = self._collection.find_one(
            {"email": normalized_email}
        )

        if document is None:
            return None

        return user_from_document(document)

    def update(self, user: User) -> User | None:
        """Полностью заменить документ пользователя по id."""
        if not isinstance(user, User):
            raise TypeError("user must be a User dataclass")

        object_id = parse_object_id(user.id)

        if object_id is None:
            return None

        user.updated_at = datetime.now(timezone.utc)

        document = user_to_document(user)
        document["_id"] = object_id

        result = self._collection.replace_one(
            {"_id": object_id},
            document,
        )

        if result.matched_count == 0:
            return None

        return user
