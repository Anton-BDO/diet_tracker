"""Тесты загрузчика общего справочника продуктов."""

import json
from types import SimpleNamespace

import mongomock
import pytest

from backend.domain.models import Product
from backend.repositories.product_repository import ProductRepository
from scripts import seed_products


def _product_data(name="Овсяные хлопья"):
    return {
        "name": name,
        "kcal": 366,
        "protein": 12.3,
        "fat": 6.1,
        "carbs": 61.8,
    }


def _write_products(path, products):
    path.write_text(
        json.dumps(products, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def test_seed_products_inserts_system_products_with_current_schema(tmp_path):
    database = mongomock.MongoClient().diet_tracker
    products_file = _write_products(
        tmp_path / "products.json",
        [_product_data(), _product_data("Куриная грудка")],
    )

    added, skipped = seed_products.seed_products(
        database,
        products_file,
    )

    assert (added, skipped) == (2, 0)
    assert database.products.count_documents({}) == 2
    stored = database.products.find_one(
        {"name": "Овсяные хлопья"}
    )
    assert stored["owner_id"] is None
    assert stored["name_lower"] == "овсяные хлопья"
    assert stored["kcal"] == 366
    assert "calories" not in stored


def test_seed_products_is_idempotent_and_matches_casefolded_name(tmp_path):
    database = mongomock.MongoClient().diet_tracker
    repository = ProductRepository(database)
    repository.create(
        Product(
            name="ОВСЯНЫЕ ХЛОПЬЯ",
            kcal=366,
            protein=12.3,
            fat=6.1,
            carbs=61.8,
        )
    )
    products_file = _write_products(
        tmp_path / "products.json",
        [_product_data()],
    )

    first_result = seed_products.seed_products(database, products_file)
    second_result = seed_products.seed_products(database, products_file)

    assert first_result == (0, 1)
    assert second_result == (0, 1)
    assert database.products.count_documents({}) == 1


def test_seed_products_user_product_does_not_block_global_one(tmp_path):
    """Пользовательский продукт с тем же названием не мешает системному."""
    database = mongomock.MongoClient().diet_tracker
    repository = ProductRepository(database)
    repository.create(
        Product(
            name="Овсяные хлопья",
            kcal=350,
            protein=15,
            fat=5,
            carbs=50,
            owner_id="64f1a2b3c4d5e6f708192a3b",
        )
    )
    products_file = _write_products(
        tmp_path / "products.json",
        [_product_data()],
    )

    assert seed_products.seed_products(database, products_file) == (1, 0)

    stored = database.products.find_one(
        {"name_lower": "овсяные хлопья", "owner_id": None}
    )
    assert stored is not None


def test_seed_products_returns_zero_counts_for_empty_file(tmp_path):
    database = mongomock.MongoClient().diet_tracker
    products_file = _write_products(tmp_path / "empty.json", [])

    assert seed_products.seed_products(database, products_file) == (0, 0)


def test_seed_products_loads_default_seed_file():
    database = mongomock.MongoClient().diet_tracker

    added, skipped = seed_products.seed_products(database)

    total = len(json.loads(
        seed_products.PRODUCTS_FILE.read_text(encoding="utf-8")
    ))
    assert (added, skipped) == (total, 0)
    assert total >= 250
    assert database.products.count_documents({"owner_id": None}) == total
    assert seed_products.seed_products(database) == (0, total)


def test_main_uses_environment_settings_and_closes_client(monkeypatch):
    database = mongomock.MongoClient().diet_tracker

    class FakeClient:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    client = FakeClient()
    settings = SimpleNamespace(
        mongo_uri="mongodb://test-host:27017",
        db_name="test_database",
    )
    monkeypatch.setattr(seed_products, "load_settings", lambda: settings)
    monkeypatch.setattr(seed_products, "create_client", lambda uri: client)
    monkeypatch.setattr(
        seed_products,
        "get_database",
        lambda *_: database,
    )

    seed_products.main()

    assert client.closed is True
    total = len(json.loads(
        seed_products.PRODUCTS_FILE.read_text(encoding="utf-8")
    ))
    assert database.products.count_documents({}) == total


def test_main_closes_client_when_seeding_fails(monkeypatch):
    class FakeClient:
        closed = False

        def close(self):
            self.closed = True

    client = FakeClient()
    settings = SimpleNamespace(mongo_uri="mongodb://test", db_name="test")
    monkeypatch.setattr(seed_products, "load_settings", lambda: settings)
    monkeypatch.setattr(seed_products, "create_client", lambda uri: client)
    monkeypatch.setattr(seed_products, "get_database", lambda *_: object())

    def fail_seeding(*args):
        raise RuntimeError("seed failed")

    monkeypatch.setattr(seed_products, "seed_products", fail_seeding)

    with pytest.raises(RuntimeError, match="seed failed"):
        seed_products.main()

    assert client.closed is True
