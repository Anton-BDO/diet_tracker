"""Сквозные HTTP-тесты справочника продуктов."""
import threading
from urllib.parse import quote

import pytest

from backend.app import build_server
from backend.config import load_settings
from backend.domain.models import Product
from backend.repositories import ProductRepository
from tests.integration.helpers import auth_headers


@pytest.fixture
def endpoint(mongo_client, static_dir):
    settings = load_settings({
        "HOST": "127.0.0.1",
        "PORT": "0",
        "STATIC_DIR": str(static_dir),
        "DB_NAME": "diet_tracker_test",
    })
    server = build_server(settings, mongo_client)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host, port = server.server_address
    yield f"http://{host}:{port}"
    server.shutdown()
    server.server_close()


@pytest.fixture
def seed_products(db):
    """Один общий и один чужой продукт в базе."""
    products = [
        Product(name="Куриная грудка", kcal=113, protein=23.6, fat=1.9,
                carbs=0.4),
        Product(name="Гречневая крупа", kcal=132, protein=4.5, fat=1.6,
                carbs=24),
    ]
    for product in products:
        ProductRepository(db).create(product)
    return products


CUSTOM_PRODUCT = {
    "name": "Протеиновый батончик",
    "kcal": 350,
    "protein": 20,
    "fat": 12,
    "carbs": 40,
}


def _create(http, endpoint, headers, **overrides):
    body = dict(CUSTOM_PRODUCT)
    body.update(overrides)
    return http(endpoint + "/api/products", "POST", body=body,
                headers=headers)


def test_search_requires_token(endpoint, http):
    status, _, _ = http(endpoint + "/api/products")

    assert status == 401


def test_create_product_returns_201_with_owner(endpoint, http, seed_products):
    headers = auth_headers(http, endpoint)

    status, _, body = _create(http, endpoint, headers)

    assert status == 201
    assert body["name"] == "Протеиновый батончик"
    assert body["owner_id"] is not None


def test_search_without_query_returns_full_catalog(endpoint, http,
                                                   seed_products):
    headers = auth_headers(http, endpoint)

    status, _, body = http(endpoint + "/api/products", headers=headers)

    assert status == 200
    names = {product["name"] for product in body}
    assert {"Куриная грудка", "Гречневая крупа"} <= names


def test_search_is_case_insensitive_substring(endpoint, http, seed_products):
    headers = auth_headers(http, endpoint)

    status, _, body = http(
        endpoint + "/api/products?q=" + quote("кУРИН"), headers=headers,
    )

    assert status == 200
    assert [product["name"] for product in body] == ["Куриная грудка"]


def test_user_sees_own_product_and_global_but_not_foreign(
    endpoint, http, seed_products, mongo_client,
):
    settings_owner = auth_headers(http, endpoint, "owner@example.com")
    _create(http, endpoint, settings_owner)
    other = auth_headers(http, endpoint, "other@example.com")

    status, _, body = http(endpoint + "/api/products", headers=other)

    assert status == 200
    names = {product["name"] for product in body}
    assert "Куриная грудка" in names          # общий продукт виден
    assert "Протеиновый батончик" not in names  # чужой — нет


def test_regex_characters_in_query_are_literal(endpoint, http, seed_products):
    headers = auth_headers(http, endpoint)

    status, _, _ = http(
        endpoint + "/api/products?q=" + quote("(("), headers=headers,
    )

    assert status == 200


@pytest.mark.parametrize("overrides,field", [
    ({"name": "   "}, "name"),
    ({"kcal": -1}, "kcal"),
    ({"protein": "много"}, "protein"),
    ({"fat": True}, "fat"),
    ({"carbs": float("inf")}, "carbs"),
])
def test_create_product_validation(endpoint, http, overrides, field):
    headers = auth_headers(http, endpoint)

    status, _, body = _create(http, endpoint, headers, **overrides)

    assert status == 400
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["field"] == field


def test_create_product_missing_field_is_400(endpoint, http):
    headers = auth_headers(http, endpoint)
    body = dict(CUSTOM_PRODUCT)
    del body["fat"]

    status, _, response = http(
        endpoint + "/api/products", "POST", body=body, headers=headers,
    )

    assert status == 400
    assert response["error"]["field"] == "fat"
