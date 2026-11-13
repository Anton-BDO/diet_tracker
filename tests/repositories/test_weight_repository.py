"""Тесты репозитория веса."""
import pytest

from backend.domain.models import WeightLog
from backend.repositories import WeightRepository

USER_ID = "6521a3b5c9e8d761a2b3c0ff"
OTHER_ID = "6521a3b5c9e8d761a2b3c0fe"


@pytest.fixture
def repository(db):
    return WeightRepository(db)


def _log(user_id=USER_ID, weight=80, date="2026-10-07"):
    return WeightLog(user_id=user_id, weight_kg=weight, date=date)


def test_upsert_inserts_then_updates_same_document(repository):
    first = repository.upsert(_log(weight=80))
    second = repository.upsert(_log(weight=81))

    assert second.id == first.id
    assert second.weight_kg == 81
    assert second.created_at == first.created_at
    assert len(repository.get_by_period(USER_ID)) == 1


def test_two_users_may_log_same_date(repository):
    repository.upsert(_log(user_id=USER_ID, date="2026-10-07"))
    repository.upsert(_log(user_id=OTHER_ID, date="2026-10-07"))

    assert len(repository.get_by_period(USER_ID)) == 1
    assert len(repository.get_by_period(OTHER_ID)) == 1


def test_get_by_period_includes_edges_and_sorts(repository):
    for date, weight in [("2026-10-09", 82), ("2026-10-07", 80),
                         ("2026-10-08", 81)]:
        repository.upsert(_log(weight=weight, date=date))

    logs = repository.get_by_period(USER_ID, "2026-10-07", "2026-10-08")

    assert [(log.date, log.weight_kg) for log in logs] == [
        ("2026-10-07", 80.0),
        ("2026-10-08", 81.0),
    ]


def test_get_by_period_supports_open_ended_ranges(repository):
    repository.upsert(_log(weight=80, date="2026-10-07"))
    repository.upsert(_log(weight=81, date="2026-10-08"))

    assert len(repository.get_by_period(USER_ID, date_from="2026-10-08")) == 1
    assert len(repository.get_by_period(USER_ID, date_to="2026-10-07")) == 1


def test_get_latest_returns_newest_measurement(repository):
    repository.upsert(_log(weight=80, date="2026-10-07"))
    repository.upsert(_log(weight=82, date="2026-10-09"))
    repository.upsert(_log(user_id=OTHER_ID, weight=99,
                           date="2026-10-10"))

    latest = repository.get_latest(USER_ID)

    assert latest.weight_kg == 82.0
    assert latest.date == "2026-10-09"


def test_get_latest_returns_none_without_history(repository):
    assert repository.get_latest(USER_ID) is None


def test_period_methods_reject_invalid_user_id(repository):
    with pytest.raises(ValueError):
        repository.get_by_period("bad")
    assert repository.get_latest("bad") is None
