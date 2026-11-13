"""Сценарии журнала веса."""
import threading
from dataclasses import replace

from backend.domain.errors import NotFoundError, ValidationError
from backend.domain.models import WeightLog, validate_date


class WeightService:
    """Сохранение замеров с синхронизацией веса в профиле."""

    def __init__(self, users, weights):
        self._users = users
        self._weights = weights
        self._locks_guard = threading.Lock()
        self._locks = {}

    def log_weight(self, data, user_id):
        """Сохранить замер; обновить профиль по правилу свежести."""
        if not isinstance(data, dict):
            raise ValidationError("Ожидается JSON-объект")
        for field in ("weight_kg", "date"):
            if field not in data or data[field] is None:
                raise ValidationError(f"Обязательное поле: {field}", field)

        # Три шага ниже читают и пишут профиль, поэтому выполняются
        # под блокировкой: иначе параллельные запросы могут записать
        # в профиль более старый замер последним.
        with self._lock_for(user_id):
            user = self._users.get_by_id(user_id)
            if user is None:
                raise NotFoundError("Пользователь не найден")

            previous = self._weights.get_latest(user_id)
            log = self._weights.upsert(WeightLog(
                user_id=user_id,
                weight_kg=data["weight_kg"],
                date=data["date"],
            ))

            if previous is None or log.date >= previous.date:
                self._users.update(replace(user, weight_kg=log.weight_kg))

        return log

    def get_history(self, user_id, date_from=None, date_to=None):
        """История веса за период, от старых дат к новым."""
        if date_from is not None:
            validate_date(date_from, "from")
        if date_to is not None:
            validate_date(date_to, "to")
        if (date_from is not None and date_to is not None
                and date_from > date_to):
            raise ValidationError(
                "Дата from не может быть позже to",
                "from",
            )
        return self._weights.get_by_period(user_id, date_from, date_to)

    def _lock_for(self, user_id):
        """Вернуть блокировку последовательности замеров пользователя."""
        with self._locks_guard:
            if user_id not in self._locks:
                self._locks[user_id] = threading.Lock()
            return self._locks[user_id]
