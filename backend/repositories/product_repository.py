"""Репозиторий продуктов."""

import re

from backend.domain.models import Product
from backend.repositories._mapping import (
    parse_object_id,
    product_from_document,
    product_to_document,
)


class ProductRepository:
    """Работа с продуктами с фильтрацией по владельцу."""

    def __init__(self, database):
        """Инициализировать репозиторий продуктов."""
        self._collection = database["products"]

    def create(self, product: Product) -> Product:
        """Сохранить продукт и присвоить ему строковый id."""
        if not isinstance(product, Product):
            raise TypeError("product must be a Product dataclass")

        document = product_to_document(product)
        document.pop("_id", None)

        result = self._collection.insert_one(document)
        product.id = str(result.inserted_id)

        return product

    def search(self, query: str, user_id: str) -> list[Product]:
        """Найти системные и собственные продукты.

        Поиск по имени не зависит от регистра. Пустой query возвращает
        все доступные пользователю продукты.
        """
        owner_object_id = parse_object_id(user_id)

        if owner_object_id is None:
            raise ValueError(
                "user_id must be a valid MongoDB ObjectId"
            )

        if not isinstance(query, str):
            raise TypeError("query must be a string")

        # Видны только системные продукты и продукты текущего владельца.
        visibility_filter = {
            "$or": [
                {"owner_id": None},
                {"owner_id": owner_object_id},
            ]
        }

        normalized_query = query.strip().casefold()

        if normalized_query:
            visibility_filter["name_lower"] = {
                "$regex": re.escape(normalized_query)
            }

        documents = self._collection.find(
            visibility_filter
        ).sort("name_lower", 1)

        return [
            product_from_document(document)
            for document in documents
        ]

    def get_by_id(self, product_id: str, user_id: str):
        """Получить системный или собственный продукт."""
        object_id = parse_object_id(product_id)
        owner_object_id = parse_object_id(user_id)

        if object_id is None or owner_object_id is None:
            return None

        document = self._collection.find_one(
            {
                "_id": object_id,
                "$or": [
                    {"owner_id": None},
                    {"owner_id": owner_object_id},
                ],
            }
        )

        if document is None:
            return None

        return product_from_document(document)

    # Альтернативные имена методов.
    find = search
    find_by_name = search
    search_visible = search
    save = create
