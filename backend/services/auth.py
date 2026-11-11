"""Сценарии регистрации, входа и выхода."""
import secrets
from datetime import timedelta

from backend.domain.errors import (
    ConflictError,
    UnauthorizedError,
    ValidationError,
)
from backend.domain.models import Session, User, utc_now
from backend.domain.passwords import (
    PASSWORD_MIN_LENGTH,
    hash_password,
    verify_password,
)

SESSION_TTL = timedelta(days=7)

_REGISTER_FIELDS = (
    "email",
    "password",
    "name",
    "sex",
    "birth_date",
    "height_cm",
    "weight_kg",
    "activity",
    "goal",
)


class AuthService:
    """Регистрация, вход и выход через репозитории пользователей и сессий."""

    def __init__(self, users, sessions, clock=None):
        self._users = users
        self._sessions = sessions
        self._clock = clock or utc_now

    def register(self, data):
        """Создать пользователя и сессию; вернуть токен и пользователя."""
        _require_fields(data, _REGISTER_FIELDS)

        password = data["password"]
        if (not isinstance(password, str)
                or len(password) < PASSWORD_MIN_LENGTH):
            raise ValidationError(
                "Пароль должен быть не короче "
                f"{PASSWORD_MIN_LENGTH} символов",
                "password",
            )

        email = data["email"]
        if not isinstance(email, str):
            raise ValidationError("Email должен быть строкой", "email")
        if self._users.get_by_email(email) is not None:
            raise ConflictError("Email уже занят", "email")

        user = User(
            email=email,
            password_hash=hash_password(password),
            name=data["name"],
            sex=data["sex"],
            birth_date=data["birth_date"],
            height_cm=data["height_cm"],
            weight_kg=data["weight_kg"],
            activity=data["activity"],
            goal=data["goal"],
        )
        user = self._users.create(user)
        token = self._create_session(user.id)
        return token, user

    def login(self, email, password):
        """Проверить учётные данные и вернуть токен новой сессии."""
        if not isinstance(email, str) or not isinstance(password, str):
            raise ValidationError("Укажите email и пароль", "email")

        user = self._users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Неверный email или пароль")
        return self._create_session(user.id)

    def logout(self, token):
        """Удалить текущую сессию; вернуть True, если она существовала."""
        return self._sessions.delete_by_token(token)

    def _create_session(self, user_id):
        """Создать и сохранить сессию с токеном, вернуть токен."""
        session = Session(
            token=secrets.token_urlsafe(32),
            user_id=user_id,
            expires_at=self._clock() + SESSION_TTL,
        )
        self._sessions.create(session)
        return session.token


def _require_fields(data, names):
    """Проверить, что все обязательные поля присутствуют и не пустые."""
    if not isinstance(data, dict):
        raise ValidationError("Ожидается JSON-объект")
    for name in names:
        if name not in data or data[name] is None:
            raise ValidationError(f"Обязательное поле: {name}", name)
