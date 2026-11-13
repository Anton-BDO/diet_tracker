"""Обработчики справочника продуктов."""
from backend.api.http_utils import json_response
from backend.api.serializers import product_to_public


def make_search_products_handler(products_service):
    """Создать обработчик GET /api/products."""

    def search_products(request):
        entries = products_service.search(
            request.query.get("q"),
            request.user_id,
        )
        return json_response(200, [
            product_to_public(product) for product in entries
        ])

    return search_products


def make_create_product_handler(products_service):
    """Создать обработчик POST /api/products."""

    def create_product(request):
        product = products_service.create(request.json(), request.user_id)
        return json_response(201, product_to_public(product))

    return create_product
