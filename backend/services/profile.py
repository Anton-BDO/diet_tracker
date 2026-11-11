"""Сценарии просмотра и обновления профиля."""
from dataclasses import replace

from backend.domain.errors import NotFoundError, ValidationError
from backend.domain.models import age_on
from backend.domain.nutrition import calculate_daily_targets

_ALLOWED_FIELDS = ("height_cm", "weight_kg", "activity", "goal")


class ProfileService:
    """Возвращает профиль с нормой и обновляет разрешённые поля."""

    def __init__(self, users):
        self._users = users

    def get_profile(self, user_id):
        """Вернуть пользователя и его норму, вычисленную на сегодня."""
        user = self._load_user(user_id)
        return user, self.norm_for(user)

    def update_profile(self, user_id, changes):
        """Обновить разрешённые поля и вернуть профиль с новой нормой."""
        user = self._load_user(user_id)
        _validate_changes(changes)
        updated = self._users.update(replace(user, **changes))
        if updated is None:
            raise NotFoundError("Пользователь не найден")
        return updated, self.norm_for(updated)

    def norm_for(self, user):
        """Вычислить норму КБЖУ по текущим параметрам пользователя."""
        age = age_on(user.birth_date)
        return calculate_daily_targets(
            user.sex,
            user.weight_kg,
            user.height_cm,
            age,
            user.activity,
            user.goal,
        )

    def _load_user(self, user_id):
        """Загрузить пользователя или бросить доменную 404."""
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Пользователь не найден")
        return user


def _validate_changes(changes):
    """Проверить, что передано хотя бы одно разрешённое поле."""
    if not isinstance(changes, dict) or not changes:
        raise ValidationError("Передайте хотя бы одно поле")
    unknown = sorted(set(changes) - set(_ALLOWED_FIELDS))
    if unknown:
        raise ValidationError(
            "Нельзя изменить поле: " + ", ".join(unknown),
            unknown[0],
        )
