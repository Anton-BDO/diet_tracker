"""Репозиторий дневника питания."""

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
        """Добавить запись с преобразованными ссылками."""
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
        """Вернуть записи пользователя за день."""
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

    def delete(self, entry_id: str) -> bool:
        """Физически удалить запись по id.

        Вернуть True, если запись существовала.
        """
        object_id = parse_object_id(entry_id)

        if object_id is None:
            return False

        result = self._collection.delete_one(
            {"_id": object_id}
        )

        return result.deleted_count == 1

    find_by_user_and_date = get_by_user_and_date
    get_for_day = get_by_user_and_date
    save = create
