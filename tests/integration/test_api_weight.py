"""Сквозные HTTP-тесты журнала веса."""
import threading

import pytest

from backend.app import build_server
from backend.config import load_settings
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


def _log_weight(http, endpoint, headers, weight=80, date="2026-10-07"):
    return http(
        endpoint + "/api/weight",
        "POST",
        body={"weight_kg": weight, "date": date},
        headers=headers,
    )


def _profile_weight(http, endpoint, headers):
    status, _, body = http(endpoint + "/api/profile", headers=headers)
    assert status == 200
    return body["weight_kg"]


def test_log_weight_returns_201_and_updates_profile(endpoint, http):
    headers = auth_headers(http, endpoint)   # исходный вес 80

    status, _, body = _log_weight(http, endpoint, headers,
                                  weight=79.5)

    assert status == 201
    assert body["date"] == "2026-10-07"
    assert body["weight_kg"] == 79.5
    assert _profile_weight(http, endpoint, headers) == 79.5


def test_repeat_log_same_date_updates_single_document(endpoint, http, db):
    headers = auth_headers(http, endpoint)
    _log_weight(http, endpoint, headers, weight=79, date="2026-10-07")

    status, _, body = _log_weight(http, endpoint, headers,
                                  weight=78.5, date="2026-10-07")

    assert status == 201
    assert body["weight_kg"] == 78.5
    assert db["weight_logs"].count_documents({}) == 1
    assert _profile_weight(http, endpoint, headers) == 78.5


def test_older_measurement_does_not_change_profile(endpoint, http):
    headers = auth_headers(http, endpoint)
    _log_weight(http, endpoint, headers, weight=79, date="2026-10-07")

    _log_weight(http, endpoint, headers, weight=95, date="2026-10-01")

    assert _profile_weight(http, endpoint, headers) == 79.0


def test_history_is_sorted_and_isolated(endpoint, http):
    first = auth_headers(http, endpoint, "first@example.com")
    second = auth_headers(http, endpoint, "second@example.com")
    _log_weight(http, endpoint, first, weight=81, date="2026-10-09")
    _log_weight(http, endpoint, first, weight=80, date="2026-10-07")
    _log_weight(http, endpoint, second, weight=99, date="2026-10-08")

    status, _, body = http(endpoint + "/api/weight", headers=first)

    assert status == 200
    assert [(row["date"], row["weight_kg"]) for row in body] == [
        ("2026-10-07", 80.0),
        ("2026-10-09", 81.0),
    ]


def test_history_with_period_filter(endpoint, http):
    headers = auth_headers(http, endpoint)
    _log_weight(http, endpoint, headers, weight=80, date="2026-10-07")
    _log_weight(http, endpoint, headers, weight=81, date="2026-10-08")
    _log_weight(http, endpoint, headers, weight=82, date="2026-10-09")

    status, _, body = http(
        endpoint + "/api/weight?from=2026-10-08&to=2026-10-09",
        headers=headers,
    )

    assert status == 200
    assert [row["date"] for row in body] == ["2026-10-08", "2026-10-09"]


def test_history_single_boundary_allowed(endpoint, http):
    headers = auth_headers(http, endpoint)
    _log_weight(http, endpoint, headers, weight=80, date="2026-10-07")

    status, _, _ = http(
        endpoint + "/api/weight?from=2026-10-07", headers=headers,
    )
    status_to, _, _ = http(
        endpoint + "/api/weight?to=2026-10-07", headers=headers,
    )

    assert status == 200
    assert status_to == 200


@pytest.mark.parametrize("query,field", [
    ("from=2026-10-08&to=2026-10-07", "from"),
    ("from=2026-13-40", "from"),
    ("to=2026-2-01", "to"),
])
def test_history_invalid_range_is_400(endpoint, http, query, field):
    headers = auth_headers(http, endpoint)

    status, _, body = http(
        f"{endpoint}/api/weight?{query}", headers=headers,
    )

    assert status == 400
    assert body["error"]["field"] == field


@pytest.mark.parametrize("payload,field", [
    ({"date": "2026-10-07"}, "weight_kg"),
    ({"weight_kg": 80}, "date"),
    ({"weight_kg": 20, "date": "2026-10-07"}, "weight_kg"),
    ({"weight_kg": 80, "date": "2026-13-40"}, "date"),
])
def test_log_weight_validation(endpoint, http, payload, field):
    headers = auth_headers(http, endpoint)

    status, _, body = http(
        endpoint + "/api/weight", "POST", body=payload, headers=headers,
    )

    assert status == 400
    assert body["error"]["field"] == field


def test_weight_endpoints_require_token(endpoint, http):
    assert http(endpoint + "/api/weight")[0] == 401
    assert http(endpoint + "/api/weight", "POST",
                body={"weight_kg": 80, "date": "2026-10-07"})[0] == 401
