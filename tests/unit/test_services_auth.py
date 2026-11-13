"""Тесты сервиса авторизации на поддельных репозиториях."""
from datetime import datetime, timezone

import pytest

from backend.domain.errors import (
    ConflictError,
    UnauthorizedError,
    ValidationError,
)
from backend.services.auth import AuthService, SESSION_TTL

NOW = datetime(2026, 11, 11, 12, tzinfo=timezone.utc)

VALID_DATA = {
    "email": "User@Example.com",
    "password": "strongpassword123",
    "name": "Алексей",
    "sex": "male",
    "birth_date": "1996-03-15",
    "height_cm": 180,
    "weight_kg": 80,
    "activity": 1.55,
    "goal": "lose",
}


class FakeUsers:
    """Минимальный репозиторий пользователей в памяти."""

    def __init__(self):
        self.by_id = {}
        self.by_email = {}
        self.created = []

    def get_by_email(self, email):
        if not isinstance(email, str):
            return None
        return self.by_email.get(email.strip().lower())

    def get_by_id(self, user_id):
        return self.by_id.get(user_id)

    def create(self, user):
        user.id = str(len(self.by_id) + 1)
        self.by_id[user.id] = user
        self.by_email[user.email] = user
        self.created.append(user)
        return user


class FakeSessions:
    """Минимальный репозиторий сессий в памяти."""

    def __init__(self):
        self.by_token = {}

    def create(self, session):
        session.id = str(len(self.by_token) + 1)
        self.by_token[session.token] = session
        return session

    def get_by_token(self, token):
        return self.by_token.get(token)

    def delete_by_token(self, token):
        return self.by_token.pop(token, None) is not None


@pytest.fixture
def users():
    return FakeUsers()


@pytest.fixture
def sessions():
    return FakeSessions()


@pytest.fixture
def service(users, sessions):
    return AuthService(users, sessions, clock=lambda: NOW)


def _register(service, **overrides):
    data = dict(VALID_DATA)
    data.update(overrides)
    return service.register(data)


def test_register_returns_token_and_stores_user_and_session(service, users,
                                                            sessions):
    token, user = _register(service)

    assert isinstance(token, str) and token
    assert user.id in users.by_id
    assert users.created[0].email == "user@example.com"
    assert sessions.by_token[token].user_id == user.id
    assert sessions.by_token[token].expires_at == NOW + SESSION_TTL


def test_register_normalizes_email_case(service, users):
    _register(service, email="  ANOTHER@Example.COM ")

    assert "another@example.com" in users.by_email


def test_register_hashes_password(service, users):
    _, user = _register(service)

    stored = users.by_id[user.id].password_hash
    assert stored != VALID_DATA["password"]
    assert stored.startswith("pbkdf2_sha256$")


@pytest.mark.parametrize("field", list(VALID_DATA))
def test_register_requires_every_field(service, field):
    data = dict(VALID_DATA)
    del data[field]

    with pytest.raises(ValidationError) as exc_info:
        service.register(data)

    assert exc_info.value.field == field


def test_register_rejects_short_password(service):
    with pytest.raises(ValidationError) as exc_info:
        _register(service, password="short")

    assert exc_info.value.field == "password"


def test_register_rejects_duplicate_email(service):
    _register(service)

    with pytest.raises(ConflictError) as exc_info:
        _register(service, name="Другой")

    assert exc_info.value.field == "email"


def test_login_returns_new_token(service, sessions):
    password = VALID_DATA["password"]
    _register(service)

    token = service.login("user@example.com", password)

    assert token in sessions.by_token


@pytest.mark.parametrize("email,password", [
    ("nobody@example.com", "strongpassword123"),
    ("user@example.com", "wrong-password"),
])
def test_login_failure_is_unauthorized(service, email, password):
    _register(service)

    with pytest.raises(UnauthorizedError):
        service.login(email, password)


def test_login_with_non_string_fields_is_validation_error(service):
    with pytest.raises(ValidationError):
        service.login(None, None)


def test_logout_removes_only_current_session(service, sessions):
    _register(service)
    first = service.login("user@example.com", VALID_DATA["password"])
    second = service.login("user@example.com", VALID_DATA["password"])

    assert service.logout(first) is True

    assert first not in sessions.by_token
    assert second in sessions.by_token


def test_logout_unknown_token_returns_false(service):
    assert service.logout("no-such-token") is False
