"""Настоящий HTTP и Bearer middleware с тестовым репозиторием сессий."""
from datetime import datetime, timedelta, timezone
from http.client import HTTPConnection
import json
import threading
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import urlsplit

import pytest

from backend.api.auth import SessionRepository, make_authenticator
from backend.api.http_utils import json_response
from backend.api.router import Router
from backend.app import build_server
from backend.config import load_settings

NOW = datetime(2026, 10, 20, 10, tzinfo=timezone.utc)


@pytest.fixture
def sessions():
    records = {
        "token-a": SimpleNamespace(
            user_id="user-a", expires_at=NOW + timedelta(hours=1),
        ),
        "token-b": SimpleNamespace(
            user_id="user-b", expires_at=NOW + timedelta(hours=1),
        ),
        "expired": SimpleNamespace(user_id="user-a", expires_at=NOW),
    }
    repository = Mock(spec=SessionRepository)
    repository.get_by_token.side_effect = records.get
    return repository


@pytest.fixture
def endpoint(run_server, sessions):
    router = Router()
    # Обработчики тестовых маршрутов не обращаются к токенам.
    router.get("/api/profile", lambda r: json_response(200, {
        "user_id": r.user_id,
    }))
    router.get("/api/health", lambda r: json_response(200, {"public": True}))
    router.post("/api/auth/register", lambda r: json_response(201, {
        "user_id": r.user_id,
    }))
    router.post("/api/auth/login", lambda r: json_response(200, {
        "user_id": r.user_id,
    }))
    return run_server(router, make_authenticator(sessions, lambda: NOW))


@pytest.mark.parametrize("headers", [
    {}, {"Authorization": "Basic token-a"}, {"Authorization": "Bearer"},
    {"Authorization": "Bearer unknown"}, {"Authorization": "Bearer expired"},
    {"Authorization": "Bearer token-a token-b"},
    {"X-User-Id": "user-a"},
])
def test_profile_unauthorized_is_json_with_cors(endpoint, http, headers):
    status, response_headers, body = http(
        endpoint + "/api/profile", headers=headers,
    )
    assert status == 401
    assert body["error"]["code"] == "unauthorized"
    assert response_headers["Content-Type"].startswith("application/json")
    assert response_headers["Access-Control-Allow-Origin"] == "*"
    assert "token-a" not in json.dumps(body)


def test_valid_tokens_supply_separate_user_contexts(endpoint, http, sessions):
    for token, owner in [("token-a", "user-a"), ("token-b", "user-b")]:
        status, _, body = http(
            endpoint + "/api/profile?user_id=foreign", headers={
                "authorization": "bearer " + token, "X-User-Id": "foreign",
            },
        )
        assert status == 200
        assert body == {"user_id": owner}
    assert sessions.get_by_token.call_count == 2


@pytest.mark.parametrize("method, path, status", [
    ("GET", "/api/health", 200),
    ("POST", "/api/auth/register", 201),
    ("POST", "/api/auth/login", 200),
])
@pytest.mark.parametrize("headers", [{}, {"Authorization": "invalid"}])
def test_public_routes_bypass_token_lookup(
    endpoint, http, sessions, method, path, status, headers,
):
    got, _, body = http(endpoint + path, method, headers=headers)
    assert got == status
    if "user_id" in body:
        assert body["user_id"] is None
    sessions.get_by_token.assert_not_called()


@pytest.mark.parametrize("path", ["/api/health/private", "/api/auth/login/",
                                  "/api/auth/logout", "/api/unknown"])
def test_protection_runs_before_route_resolution(endpoint, http, path):
    assert http(endpoint + path)[0] == 401


@pytest.mark.parametrize("second_name", ["Authorization", "authorization"])
def test_repeated_authorization_is_rejected_over_http(
    endpoint, sessions, second_name,
):
    target = urlsplit(endpoint)
    connection = HTTPConnection(target.hostname, target.port, timeout=5)
    try:
        connection.putrequest("GET", "/api/profile")
        connection.putheader("Authorization", "Bearer token-a")
        connection.putheader(second_name, "Bearer token-b")
        connection.endheaders()
        response = connection.getresponse()
        body = json.loads(response.read())
        assert response.status == 401
        assert body["error"]["code"] == "unauthorized"
        sessions.get_by_token.assert_not_called()
    finally:
        connection.close()


def test_repository_failure_is_500_not_access_or_401(endpoint, sessions, http):
    sessions.get_by_token.side_effect = RuntimeError("secret database details")
    status, _, body = http(endpoint + "/api/profile", headers={
        "Authorization": "Bearer token-a",
    })
    assert status == 500
    assert body["error"]["code"] == "internal_error"
    assert "secret" not in json.dumps(body)


def test_existing_options_and_static_still_work(endpoint, sessions, http):
    status, headers, body = http(endpoint + "/api/profile", "OPTIONS")
    assert status == 204
    assert body is None
    assert "Authorization" in headers["Access-Control-Allow-Headers"]
    assert http(endpoint + "/")[2] == "<h1>ok</h1>"
    sessions.get_by_token.assert_not_called()


@pytest.fixture
def app_endpoint(mongo_client, static_dir):
    settings = load_settings({
        "HOST": "127.0.0.1", "PORT": "0", "STATIC_DIR": str(static_dir),
    })
    # Настоящая сборка приложения без отсутствующего пока репозитория.
    server = build_server(settings, mongo_client)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host, port = server.server_address
    yield f"http://{host}:{port}"
    server.shutdown()
    server.server_close()


def test_actual_app_profile_without_token_is_401(app_endpoint, http):
    status, _, body = http(app_endpoint + "/api/profile")
    assert status == 401
    assert body["error"]["code"] == "unauthorized"


def test_actual_app_without_repository_fails_closed(app_endpoint, http):
    status, _, body = http(app_endpoint + "/api/profile", headers={
        "Authorization": "Bearer any-token",
    })
    assert status == 500
    assert body["error"]["code"] == "internal_error"
    assert http(app_endpoint + "/api/health")[0] == 200


def test_build_server_binds_session_dependency(
    mongo_client, static_dir, sessions, http,
):
    settings = load_settings({
        "HOST": "127.0.0.1", "PORT": "0", "STATIC_DIR": str(static_dir),
    })
    server = build_server(settings, mongo_client,
                          session_repository=sessions, clock=lambda: NOW)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host, port = server.server_address
    try:
        # Profile ещё не реализован: валидная сессия проходит к роутеру → 404.
        status, _, body = http(f"http://{host}:{port}/api/profile", headers={
            "Authorization": "Bearer token-a",
        })
        assert status == 404
        assert body["error"]["code"] == "not_found"
        sessions.get_by_token.assert_called_once_with("token-a")
    finally:
        server.shutdown()
        server.server_close()
