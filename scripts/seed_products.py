"""Загрузка общего справочника продуктов в MongoDB."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import load_settings  # noqa: E402
from backend.db import create_client, get_database  # noqa: E402
from backend.domain.models import Product  # noqa: E402
from backend.repositories.product_repository import (  # noqa: E402
    ProductRepository,
)

PRODUCTS_FILE = Path(__file__).with_name("products_seed.json")


def seed_products(database, products_file=PRODUCTS_FILE):
    """Загрузить продукты, пропуская уже существующие по name_lower.

    Возвращает пару (добавлено, пропущено).
    """
    with Path(products_file).open(encoding="utf-8") as file:
        products_data = json.load(file)

    repository = ProductRepository(database)
    added = 0
    skipped = 0

    for product_data in products_data:
        product = Product(owner_id=None, **product_data)
        if repository.exists_by_name_lower(product.name_lower):
            skipped += 1
            continue

        repository.create(product)
        added += 1

    return added, skipped


def main():
    """Запустить загрузку с настройками подключения из окружения."""
    settings = load_settings()
    client = create_client(settings.mongo_uri)

    try:
        database = get_database(client, settings.db_name)
        added, skipped = seed_products(database)
        print(
            "Справочник продуктов: "
            f"добавлено {added}, пропущено {skipped}."
        )
    finally:
        client.close()


if __name__ == "__main__":  # pragma: no cover
    main()
