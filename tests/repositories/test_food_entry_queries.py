"""Тесты новых методов репозитория дневника."""
import pytest

from backend.domain.models import FoodEntry
from backend.repositories import FoodEntryRepository


def _entry(user_id, grams, date, meal="lunch"):
    return FoodEntry(
        user_id=user_id,
        product_id="6521a3b5c9e8d761a2b3c001",
        product_name="Куриная грудка",
        grams=grams,
        meal=meal,
        date=date,
        kcal=grams,
        protein=1.0,
        fat=1.0,
        carbs=1.0,
    )


@pytest.fixture
def repository(db):
    return FoodEntryRepository(db)


@pytest.fixture
def owner_id():
    return "6521a3b5c9e8d761a2b3c0ff"


def test_get_by_id_returns_entry_for_owner(repository, owner_id):
    saved = repository.create(_entry(owner_id, 100, "2026-10-07"))

    loaded = repository.get_by_id(saved.id, owner_id)

    assert loaded is not None
    assert loaded.id == saved.id


def test_get_by_id_hides_foreign_entry(repository, owner_id):
    saved = repository.create(_entry(owner_id, 100, "2026-10-07"))

    assert repository.get_by_id(saved.id, "6521a3b5c9e8d761a2b3c0fe") is None


def test_get_by_id_invalid_id_returns_none(repository, owner_id):
    saved = repository.create(_entry(owner_id, 50, "2026-10-01"))

    assert repository.get_by_id("not-an-id", owner_id) is None
    assert repository.get_by_id(saved.id, "not-an-id") is None


def test_get_by_user_and_period_includes_both_edges(repository, owner_id):
    repository.create(_entry(owner_id, 100, "2026-10-06"))
    repository.create(_entry(owner_id, 200, "2026-10-07"))
    repository.create(_entry(owner_id, 300, "2026-10-08"))
    repository.create(_entry(owner_id, 400, "2026-10-09"))

    entries = repository.get_by_user_and_period(
        owner_id, "2026-10-07", "2026-10-08",
    )

    assert [entry.grams for entry in entries] == [200, 300]


def test_get_by_user_and_period_sorts_by_date(repository, owner_id):
    repository.create(_entry(owner_id, 100, "2026-10-09"))
    repository.create(_entry(owner_id, 50, "2026-10-07"))
    repository.create(_entry(owner_id, 200, "2026-10-08"))

    entries = repository.get_by_user_and_period(
        owner_id, "2026-10-01", "2026-10-31",
    )

    assert [entry.date for entry in entries] == [
        "2026-10-07", "2026-10-08", "2026-10-09",
    ]


def test_get_all_by_user_isolated_and_sorted(repository, owner_id):
    repository.create(_entry(owner_id, 100, "2026-10-09"))
    repository.create(_entry(owner_id, 200, "2026-10-07"))
    repository.create(_entry("6521a3b5c9e8d761a2b3c0fe", 300, "2026-10-01"))

    entries = repository.get_all_by_user(owner_id)

    assert [entry.grams for entry in entries] == [200, 100]


def test_period_methods_reject_invalid_user_id(repository):
    with pytest.raises(ValueError):
        repository.get_by_user_and_period("bad", "2026-10-01", "2026-10-02")
    with pytest.raises(ValueError):
        repository.get_all_by_user("bad")
