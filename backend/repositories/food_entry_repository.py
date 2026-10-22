"""Репозиторий дневника питания."""

from datetime import datetime, timezone

from backend.domain.models import FoodEntry
from backend.repositories._mapping import (
    food_entry_from_document,
    food_entry_to_document,
    parse_object_id,
)


class FoodEntryRepository:
    """Работа с записями дневника питания."""

    def __init__(self, database):
        """Инициализировать репозиторий записей дневника."""
        self._collection = database["food_entries"]

    def create(self, entry: FoodEntry) -> FoodEntry:
        """Создать запись дневника и назначить ей id."""
        if not isinstance(entry, FoodEntry):
            raise TypeError("entry must be a FoodEntry dataclass")

        document = food_entry_to_document(entry)
        document.pop("_id", None)

        result = self._collection.insert_one(document)
        entry.id = str(result.inserted_id)

        return entry

    def get_by_user_and_date(
        self,
        user_id: str,
        date: str,
    ) -> list[FoodEntry]:
        """Получить записи пользователя за указанный день."""
        user_object_id = parse_object_id(user_id)

        if user_object_id is None:
            raise ValueError(
                "user_id must be a valid MongoDB ObjectId"
            )

        documents = self._collection.find(
            {
                "user_id": user_object_id,
                "date": date,
            }
        ).sort(
            [
                ("created_at", 1),
                ("_id", 1),
            ]
        )

        return [
            food_entry_from_document(document)
            for document in documents
        ]

    def update(
        self,
        entry: FoodEntry,
        user_id: str,
    ) -> FoodEntry | None:
        """Обновить граммы и приём пищи своей записи."""
        if not isinstance(entry, FoodEntry):
            raise TypeError("entry must be a FoodEntry dataclass")

        entry_object_id = parse_object_id(entry.id)
        user_object_id = parse_object_id(user_id)

        if entry_object_id is None or user_object_id is None:
            return None

        updated_at = datetime.now(timezone.utc)

        result = self._collection.update_one(
            {
                "_id": entry_object_id,
                "user_id": user_object_id,
            },
            {
                "$set": {
                    "grams": float(entry.grams),
                    "meal": entry.meal,
                    "updated_at": updated_at,
                }
            },
        )

        if result.matched_count == 0:
            return None

        entry.updated_at = updated_at
        return entry

    def delete(self, entry_id: str, user_id: str) -> bool:
        """Удалить запись, только если она принадлежит пользователю."""
        entry_object_id = parse_object_id(entry_id)
        user_object_id = parse_object_id(user_id)

        if entry_object_id is None or user_object_id is None:
            return False

        result = self._collection.delete_one(
            {
                "_id": entry_object_id,
                "user_id": user_object_id,
            }
        )

        return result.deleted_count == 1
