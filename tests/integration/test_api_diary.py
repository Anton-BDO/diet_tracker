"""Сквозные HTTP-тесты дневника питания."""
import threading

import pytest

from backend.app import build_server
from backend.config import load_settings
from backend.domain.models import Product
from backend.repositories import ProductRepository
from tests.integration.helpers import auth_headers, expected_norm


@pytest.fixture
def endpoint(mongo_client, static_dir, db):
    settings = load_settings({
        "HOST": "127.0.0.1",
        "PORT": "0",
        "STATIC_DIR": str(static_dir),
        "DB_NAME": "diet_tracker_test",
    })
    server = build_server(settings, mongo_client)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host, port = server.server_address
    ProductRepository(db).create(Product(
        name="Куриная грудка", kcal=113, protein=23.6, fat=1.9, carbs=0.4,
    ))
    yield f"http://{host}:{port}"
    server.shutdown()
    server.server_close()


def _product_id(http, endpoint, headers):
    status, _, body = http(endpoint + "/api/products", headers=headers)
    assert status == 200
    return body[0]["id"]


def _create_entry(http, endpoint, headers, product_id, **overrides):
    payload = {
        "product_id": product_id,
        "grams": 250,
        "meal": "lunch",
        "date": "2026-10-07",
    }
    payload.update(overrides)
    return http(endpoint + "/api/diary", "POST", body=payload,
                headers=headers)


def _diary(http, endpoint, headers, date="2026-10-07"):
    return http(
        f"{endpoint}/api/diary?date={date}", headers=headers,
    )


def test_create_entry_calculates_portion(endpoint, http):
    headers = auth_headers(http, endpoint)
    product_id = _product_id(http, endpoint, headers)

    status, _, body = _create_entry(
        http, endpoint, headers, product_id,
    )

    assert status == 201
    assert body["product_name"] == "Куриная грудка"
    assert body["grams"] == 250
    assert body["kcal"] == 282.5
    assert body["meal"] == "lunch"


def test_day_summary_totals_remaining_and_success(endpoint, http):
    headers = auth_headers(http, endpoint)
    product_id = _product_id(http, endpoint, headers)
    _create_entry(http, endpoint, headers, product_id, grams=2000)
    _create_entry(http, endpoint, headers, product_id, grams=100)

    status, _, body = _diary(http, endpoint, headers)

    assert status == 200
    assert body["date"] == "2026-10-07"
    assert len(body["entries"]) == 2
    assert body["totals"]["kcal"] == 2373.0
    assert body["remaining"]["kcal"] == (
        expected_norm()["kcal"] - body["totals"]["kcal"]
    )
    assert body["is_success"] is True
    assert body["norm"] == expected_norm()


def test_empty_day_is_not_success(endpoint, http):
    headers = auth_headers(http, endpoint)

    status, _, body = _diary(http, endpoint, headers)

    assert status == 200
    assert body["entries"] == []
    assert body["totals"]["kcal"] == 0
    assert body["is_success"] is False


@pytest.mark.parametrize("bad_date", ["2026-13-40", "2026-2-01", ""])
def test_day_with_invalid_date_is_400(endpoint, http, bad_date):
    headers = auth_headers(http, endpoint)

    status, _, body = _diary(http, endpoint, headers, bad_date)

    assert status == 400
    assert body["error"]["field"] == "date"


def test_patch_entry_recalculates_nutrients(endpoint, http):
    headers = auth_headers(http, endpoint)
    product_id = _product_id(http, endpoint, headers)
    _, _, created = _create_entry(http, endpoint, headers, product_id)

    status, _, body = http(
        f"{endpoint}/api/diary/{created['id']}",
        "PATCH",
        body={"grams": 100},
        headers=headers,
    )

    assert status == 200
    assert body["grams"] == 100
    assert body["kcal"] == 113.0


def test_patch_entry_rejects_unknown_field(endpoint, http):
    headers = auth_headers(http, endpoint)
    product_id = _product_id(http, endpoint, headers)
    _, _, created = _create_entry(http, endpoint, headers, product_id)

    status, _, body = http(
        f"{endpoint}/api/diary/{created['id']}",
        "PATCH",
        body={"date": "2026-10-08"},
        headers=headers,
    )

    assert status == 400


def test_delete_entry_then_404(endpoint, http):
    headers = auth_headers(http, endpoint)
    product_id = _product_id(http, endpoint, headers)
    _, _, created = _create_entry(http, endpoint, headers, product_id)

    status, _, body = http(
        f"{endpoint}/api/diary/{created['id']}", "DELETE", headers=headers,
    )

    assert status == 204
    assert body is None
    _, _, day = _diary(http, endpoint, headers)
    assert day["entries"] == []
    assert http(
        f"{endpoint}/api/diary/{created['id']}", "DELETE", headers=headers,
    )[0] == 404


def test_foreign_user_cannot_touch_entry(endpoint, http):
    owner = auth_headers(http, endpoint, "owner@example.com")
    intruder = auth_headers(http, endpoint, "intruder@example.com")
    product_id = _product_id(http, endpoint, owner)
    _, _, created = _create_entry(http, endpoint, owner, product_id)

    target = f"{endpoint}/api/diary/{created['id']}"
    assert http(target, "PATCH", body={"grams": 100},
                headers=intruder)[0] == 404
    assert http(target, "DELETE", headers=intruder)[0] == 404
    _, _, day = _diary(http, endpoint, intruder)
    assert day["entries"] == []


def test_cannot_create_entry_with_foreign_product(endpoint, http):
    owner = auth_headers(http, endpoint, "owner@example.com")
    intruder = auth_headers(http, endpoint, "intruder@example.com")
    _, _, product = http(
        endpoint + "/api/products",
        "POST",
        body={
            "name": "Личный продукт", "kcal": 100, "protein": 1,
            "fat": 1, "carbs": 1,
        },
        headers=owner,
    )

    status, _, _ = _create_entry(
        http, endpoint, intruder, product["id"],
    )

    assert status == 404


def test_create_entry_invalid_grams_is_400(endpoint, http):
    headers = auth_headers(http, endpoint)
    product_id = _product_id(http, endpoint, headers)

    status, _, body = _create_entry(
        http, endpoint, headers, product_id, grams=0,
    )

    assert status == 400
    assert body["error"]["field"] == "grams"


def test_invalid_entry_id_is_404_not_500(endpoint, http):
    headers = auth_headers(http, endpoint)

    status, _, body = http(
        f"{endpoint}/api/diary/not-an-id",
        "PATCH",
        body={"grams": 100},
        headers=headers,
    )

    assert status == 404
    assert body["error"]["code"] == "not_found"
