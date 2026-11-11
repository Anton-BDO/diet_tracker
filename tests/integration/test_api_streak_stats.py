"""Сквозные HTTP-тесты серий и статистики калорий."""
import threading

import pytest

from backend.app import build_server
from backend.config import load_settings
from backend.domain.models import Product
from backend.repositories import ProductRepository
from tests.integration.helpers import auth_headers, expected_norm

TODAY = "2026-10-20"


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
    _, _, body = http(endpoint + "/api/products", headers=headers)
    return body[0]["id"]


def _eat(http, endpoint, headers, product_id, grams, date):
    status, _, body = http(
        endpoint + "/api/diary",
        "POST",
        body={
            "product_id": product_id,
            "grams": grams,
            "meal": "lunch",
            "date": date,
        },
        headers=headers,
    )
    assert status == 201, body


def _headers_with_diary(http, endpoint, email="user@example.com"):
    """Пользователь с двумя успешными днями: 18 и 19 октября."""
    headers = auth_headers(http, endpoint, email)
    product_id = _product_id(http, endpoint, headers)
    _eat(http, endpoint, headers, product_id, 2000, "2026-10-18")
    _eat(http, endpoint, headers, product_id, 2000, "2026-10-19")
    return headers


def test_streak_counts_successful_days(endpoint, http):
    headers = _headers_with_diary(http, endpoint)

    status, _, body = http(
        f"{endpoint}/api/streak?today={TODAY}", headers=headers,
    )

    assert status == 200
    assert body == {"current": 2, "record": 2}


def test_streak_isolated_between_users(endpoint, http):
    _headers_with_diary(http, endpoint, "first@example.com")
    second = auth_headers(http, endpoint, "second@example.com")

    _, _, body = http(f"{endpoint}/api/streak?today={TODAY}",
                      headers=second)

    assert body == {"current": 0, "record": 0}


def test_streak_invalid_today_is_400(endpoint, http):
    headers = auth_headers(http, endpoint)

    status, _, body = http(
        f"{endpoint}/api/streak?today=2026-13-40", headers=headers,
    )

    assert status == 400
    assert body["error"]["field"] == "today"


def test_stats_returns_each_day_with_kcal(endpoint, http):
    headers = _headers_with_diary(http, endpoint)

    status, _, body = http(
        f"{endpoint}/api/stats/calories?days=3&today={TODAY}",
        headers=headers,
    )

    assert status == 200
    assert body["norm_kcal"] == expected_norm()["kcal"]
    assert [(day["date"], day["kcal"]) for day in body["days"]] == [
        ("2026-10-18", 2260.0),
        ("2026-10-19", 2260.0),
        ("2026-10-20", 0.0),
    ]
    assert [day["is_success"] for day in body["days"]] == [
        True, True, False,
    ]


@pytest.mark.parametrize("query", ["days=abc", "days=0", "days=91",
                                   "days=7.5", "today=2026-2-01",
                                   "days=%C2%B2"])
def test_stats_invalid_params_are_400(endpoint, http, query):
    headers = auth_headers(http, endpoint)

    status, _, body = http(
        f"{endpoint}/api/stats/calories?{query}", headers=headers,
    )

    assert status == 400
    assert body["error"]["code"] == "validation_error"


def test_stats_days_defaults_to_7(endpoint, http):
    headers = _headers_with_diary(http, endpoint)

    status, _, body = http(
        f"{endpoint}/api/stats/calories?today={TODAY}", headers=headers,
    )

    assert status == 200
    assert len(body["days"]) == 7
    assert body["days"][0]["date"] == "2026-10-14"
    assert body["days"][-1]["date"] == TODAY


def test_streak_and_stats_require_token(endpoint, http):
    assert http(f"{endpoint}/api/streak?today={TODAY}")[0] == 401
    assert http(f"{endpoint}/api/stats/calories?days=7")[0] == 401
