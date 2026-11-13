"""Репозиторий журнала веса."""

from backend.domain.models import WeightLog
from backend.repositories._mapping import (
    _required_object_id,
    parse_object_id,
    weight_log_from_document,
)


class WeightRepository:
    """Upsert замеров и выборка истории веса."""

    def __init__(self, database):
        self._collection = database["weight_logs"]

    def upsert(self, log: WeightLog) -> WeightLog:
        """Сохранить замер на дату, перезаписав значение при повторе."""
        filters = {
            "user_id": _required_object_id(
                log.user_id,
                "weight_log.user_id",
            ),
            "date": log.date,
        }

        self._collection.update_one(
            filters,
            {
                "$set": {"weight_kg": float(log.weight_kg)},
                "$setOnInsert": {"created_at": log.created_at},
            },
            upsert=True,
        )

        document = self._collection.find_one(filters)
        return weight_log_from_document(document)

    def get_by_period(
        self,
        user_id: str,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[WeightLog]:
        """История за период; границы необязательны и включаются."""
        user_object_id = parse_object_id(user_id)

        if user_object_id is None:
            raise ValueError(
                "user_id must be a valid MongoDB ObjectId"
            )

        filters = {"user_id": user_object_id}
        date_filter = {}
        if date_from is not None:
            date_filter["$gte"] = date_from
        if date_to is not None:
            date_filter["$lte"] = date_to
        if date_filter:
            filters["date"] = date_filter

        documents = self._collection.find(filters).sort(
            [("date", 1), ("_id", 1)]
        )

        return [
            weight_log_from_document(document)
            for document in documents
        ]

    def get_latest(self, user_id: str) -> WeightLog | None:
        """Самый свежий замер пользователя или None."""
        user_object_id = parse_object_id(user_id)

        if user_object_id is None:
            return None

        document = self._collection.find_one(
            {"user_id": user_object_id},
            sort=[("date", -1)],
        )

        if document is None:
            return None

        return weight_log_from_document(document)
