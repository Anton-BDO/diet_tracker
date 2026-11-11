"""Тесты сервиса веса, включая регрессию гонки профиля."""
import threading
from dataclasses import replace

import pytest

from backend.domain.errors import ValidationError
from backend.domain.models import User
from backend.services.weight import WeightService

USER_ID = "6521a3b5c9e8d761a2b3c0ff"


def _user(weight=80):
    return User(
        id=USER_ID,
        email="user@example.com",
        password_hash="pbkdf2_sha256$1$c2FsdA==$ZGlnZXN0",
        name="Алексей",
        sex="male",
        birth_date="1996-03-15",
        height_cm=180,
        weight_kg=weight,
        activity=1.55,
        goal="lose",
    )


class FakeUsers:
    def __init__(self, user):
        self.user = user

    def get_by_id(self, user_id):
        if self.user is None or self.user.id != user_id:
            return None
        return self.user

    def update(self, user):
        self.user = user
        return user


class FakeWeights:
    """Потокобезопасные замеры в памяти."""

    def __init__(self):
        self.logs = {}
        self._guard = threading.Lock()

    def upsert(self, log):
        with self._guard:
            self.logs[log.date] = log
        log.id = log.date
        return log

    def get_latest(self, user_id):
        with self._guard:
            if not self.logs:
                return None
            latest_date = max(self.logs)
            return self.logs[latest_date]

    def get_by_period(self, user_id, date_from=None, date_to=None):
        with self._guard:
            dates = sorted(
                date for date in self.logs
                if (date_from is None or date >= date_from)
                and (date_to is None or date <= date_to)
            )
            return [replace(self.logs[date]) for date in dates]


@pytest.fixture
def users():
    return FakeUsers(_user())


@pytest.fixture
def weights():
    return FakeWeights()


@pytest.fixture
def service(users, weights):
    return WeightService(users, weights)


def test_log_weight_updates_profile_for_first_measurement(
    service, users, weights,
):
    log = service.log_weight({"weight_kg": 79.5, "date": "2026-10-07"},
                             USER_ID)

    assert log.weight_kg == 79.5
    assert users.user.weight_kg == 79.5
    assert weights.get_latest(USER_ID).date == "2026-10-07"


def test_log_weight_rejects_bad_values(service):
    with pytest.raises(ValidationError):
        service.log_weight({"weight_kg": 10, "date": "2026-10-07"},
                           USER_ID)
    with pytest.raises(ValidationError):
        service.log_weight({"weight_kg": 80, "date": "2026-13-40"},
                           USER_ID)


def test_racing_measurements_keep_latest_date_in_profile():
    """Параллельные замеры разных дат не должны испортить профиль.

    Без блокировки оба потока читают «прежний свежий замер» одновременно
    и более старый замер может записаться в профиль последним.
    """
    for _ in range(25):
        users = FakeUsers(_user())
        service = WeightService(users, FakeWeights())
        barrier = threading.Barrier(3)

        def log(date, weight):
            barrier.wait()
            service.log_weight(
                {"weight_kg": weight, "date": date}, USER_ID,
            )

        threads = [
            threading.Thread(target=log, args=("2026-10-02", 95)),
            threading.Thread(target=log, args=("2026-10-01", 90)),
        ]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join()

        assert users.user.weight_kg == 95.0, \
            "профиль обновлён более старым замером"
