"""Тесты сервиса дневника на поддельных репозиториях."""
import pytest

from backend.domain.errors import NotFoundError, ValidationError
from backend.domain.models import Product, User
from backend.services.diary import DiaryService

USER_ID = "6521a3b5c9e8d761a2b3c0ff"
OTHER_ID = "6521a3b5c9e8d761a2b3c0fe"

PRODUCT = Product(
    id="6521a3b5c9e8d761a2b3c001",
    name="Куриная грудка",
    kcal=113,
    protein=23.6,
    fat=1.9,
    carbs=0.4,
)

USER = User(
    id=USER_ID,
    email="user@example.com",
    password_hash="pbkdf2_sha256$1$c2FsdA==$ZGlnZXN0",
    name="Алексей",
    sex="male",
    birth_date="1996-03-15",
    height_cm=180,
    weight_kg=80,
    activity=1.55,
    goal="lose",
)

NORM = {"kcal": 2345, "protein": 176, "fat": 78, "carbs": 235}


class FakeProducts:
    """Продукты с фильтром владельца, как настоящий репозиторий."""

    def __init__(self, product=None):
        self.product = product

    def get_by_id(self, product_id, user_id):
        if self.product is None or self.product.id != product_id:
            return None
        if self.product.owner_id not in (None, user_id):
            return None
        return self.product


class FakeEntries:
    """Записи в памяти с теми же правилами владельца."""

    def __init__(self):
        self.items = {}
        self.next_id = 1

    def create(self, entry):
        entry.id = str(self.next_id)
        self.next_id += 1
        self.items[entry.id] = entry
        return entry

    def get_by_user_and_date(self, user_id, date):
        return [
            entry for entry in self.items.values()
            if entry.user_id == user_id and entry.date == date
        ]

    def get_by_id(self, entry_id, user_id):
        entry = self.items.get(entry_id)
        if entry is None or entry.user_id != user_id:
            return None
        return entry

    def update(self, entry, user_id):
        current = self.get_by_id(entry.id, user_id)
        if current is None:
            return None
        self.items[entry.id] = entry
        return entry

    def delete(self, entry_id, user_id):
        if self.get_by_id(entry_id, user_id) is None:
            return False
        del self.items[entry_id]
        return True


class FakeProfiles:
    """Сервис профиля с фиксированной нормой."""

    def get_profile(self, user_id):
        if user_id != USER_ID:
            raise NotFoundError("Пользователь не найден")
        return USER, NORM


@pytest.fixture
def entries():
    return FakeEntries()


@pytest.fixture
def service(entries):
    return DiaryService(entries, FakeProducts(PRODUCT), FakeProfiles())


def _create(service, **overrides):
    data = {
        "product_id": PRODUCT.id,
        "grams": 250,
        "meal": "lunch",
        "date": "2026-10-07",
    }
    data.update(overrides)
    return service.create_entry(data, USER_ID)


def test_create_entry_snapshots_product_nutrients(service):
    entry = _create(service)

    assert entry.id is not None
    assert entry.user_id == USER_ID
    assert entry.product_name == "Куриная грудка"
    assert entry.kcal == 282.5      # 113 * 250 / 100
    assert entry.protein == 59.0
    assert entry.meal == "lunch"


def test_create_entry_unknown_product_is_not_found(service):
    with pytest.raises(NotFoundError):
        _create(service, product_id="6521a3b5c9e8d761a2b3c099")


@pytest.mark.parametrize("field", ["product_id", "grams", "meal", "date"])
def test_create_entry_requires_fields(service, field):
    data = {
        "product_id": PRODUCT.id,
        "grams": 250,
        "meal": "lunch",
        "date": "2026-10-07",
    }
    del data[field]

    with pytest.raises(ValidationError) as exc_info:
        service.create_entry(data, USER_ID)

    assert exc_info.value.field == field


def test_empty_day_is_not_success(service):
    day = service.get_day("2026-10-07", USER_ID)

    assert day["entries"] == []
    assert day["totals"] == {
        "kcal": 0, "protein": 0, "fat": 0, "carbs": 0,
    }
    assert day["norm"] == NORM
    assert day["remaining"] == NORM
    assert day["is_success"] is False


def test_day_sums_entries_and_checks_success(service):
    _create(service, grams=2000)   # 2260 ккал, в пределах ±10% от 2345
    _create(service, grams=100)    # +113 ккал

    day = service.get_day("2026-10-07", USER_ID)

    assert day["totals"]["kcal"] == 2373.0
    assert day["remaining"]["kcal"] == -28.0
    assert day["is_success"] is True


def test_day_outside_corridor_is_not_success(service):
    _create(service, grams=3000)   # 3390 ккал выше нормы +10%

    day = service.get_day("2026-10-07", USER_ID)

    assert day["is_success"] is False


def test_update_entry_recalculates_nutrients(service, entries):
    entry = _create(service, grams=250)

    updated = service.update_entry(entry.id, {"grams": 100}, USER_ID)

    assert updated.grams == 100
    assert updated.kcal == 113.0
    assert entries.items[entry.id].kcal == 113.0


def test_update_entry_meal_keeps_snapshot_nutrients(service):
    entry = _create(service, grams=250)

    updated = service.update_entry(entry.id, {"meal": "dinner"}, USER_ID)

    assert updated.meal == "dinner"
    assert updated.kcal == 282.5


def test_update_foreign_entry_is_not_found(service):
    entry = _create(service)

    with pytest.raises(NotFoundError):
        service.update_entry(entry.id, {"grams": 100}, OTHER_ID)


def test_update_rejects_unknown_or_empty_changes(service):
    entry = _create(service)

    with pytest.raises(ValidationError):
        service.update_entry(entry.id, {}, USER_ID)
    with pytest.raises(ValidationError):
        service.update_entry(entry.id, {"date": "2026-10-08"}, USER_ID)


def test_delete_entry_removes_own_record(service, entries):
    entry = _create(service)

    service.delete_entry(entry.id, USER_ID)

    assert entries.items == {}


def test_delete_foreign_entry_is_not_found(service):
    entry = _create(service)

    with pytest.raises(NotFoundError):
        service.delete_entry(entry.id, OTHER_ID)


def test_get_day_rejects_invalid_date(service):
    for bad_date in ("2026-13-40", "2026-2-01", ""):
        with pytest.raises(ValidationError) as exc_info:
            service.get_day(bad_date, USER_ID)

        assert exc_info.value.field == "date"
