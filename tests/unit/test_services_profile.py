"""Тесты сервиса профиля на поддельном репозитории."""
import pytest

from backend.domain.errors import NotFoundError, ValidationError
from backend.domain.models import User, age_on
from backend.domain.nutrition import calculate_daily_targets
from backend.services.profile import ProfileService


def _make_user(**overrides):
    fields = {
        "email": "user@example.com",
        "password_hash": "pbkdf2_sha256$1$c2FsdA==$ZGlnZXN0",
        "name": "Алексей",
        "sex": "male",
        "birth_date": "1996-03-15",
        "height_cm": 180,
        "weight_kg": 80,
        "activity": 1.55,
        "goal": "lose",
    }
    fields.update(overrides)
    return User(id="1", **fields)


def _expected_norm(user):
    age = age_on(user.birth_date)
    return calculate_daily_targets(
        user.sex,
        user.weight_kg,
        user.height_cm,
        age,
        user.activity,
        user.goal,
    )


class FakeUsers:
    """Репозиторий, помнящий последнее сохранённое состояние."""

    def __init__(self, user=None):
        self.user = user
        self.saved = []

    def get_by_id(self, user_id):
        if self.user is None or self.user.id != user_id:
            return None
        return self.user

    def update(self, user):
        self.user = user
        self.saved.append(user)
        return user


@pytest.fixture
def user():
    return _make_user()


@pytest.fixture
def service(user):
    return ProfileService(FakeUsers(user))


def test_get_profile_returns_user_and_domain_norm(service, user):
    returned, norm = service.get_profile("1")

    assert returned is user
    assert norm == _expected_norm(user)


def test_get_profile_unknown_user_is_not_found():
    service = ProfileService(FakeUsers(None))

    with pytest.raises(NotFoundError):
        service.get_profile("1")


@pytest.mark.parametrize("field,value", [
    ("height_cm", 182),
    ("weight_kg", 79.5),
    ("activity", 1.725),
    ("goal", "keep"),
])
def test_update_applies_each_allowed_field(service, field, value):
    user, norm = service.update_profile("1", {field: value})

    assert getattr(user, field) == value
    assert norm == _expected_norm(user)


def test_update_recreates_user_and_validates_new_state(service):
    with pytest.raises(ValidationError):
        service.update_profile("1", {"height_cm": 90})


def test_update_rejects_empty_changes(service):
    with pytest.raises(ValidationError):
        service.update_profile("1", {})


@pytest.mark.parametrize("field", [
    "email", "name", "sex", "birth_date", "password_hash", "id", "norm",
])
def test_update_rejects_unknown_fields(service, field):
    with pytest.raises(ValidationError) as exc_info:
        service.update_profile("1", {field: "value"})

    assert exc_info.value.field == field
