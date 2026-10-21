"""Bearer-проверка с интерфейсом сессий, без настоящей БД."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.api.auth import (
    PUBLIC_ROUTES,
    SessionRepository,
    authenticate_request,
    bearer_token,
    make_authenticator,
)
from backend.api.http_utils import HttpError, Request, json_response
from backend.api.router import Router
from backend.api.server import dispatch

NOW = datetime(2026, 10, 20, 10, tzinfo=timezone.utc)


@pytest.fixture
def sessions():
    repository = Mock(spec=SessionRepository)
    repository.get_by_token.return_value = SimpleNamespace(
        user_id="user-a", expires_at=NOW + timedelta(hours=1),
    )
    return repository


@pytest.mark.parametrize("name, value, expected", [
    ("Authorization", "Bearer token-123", "token-123"),
    ("authorization", "bearer AbC_123", "AbC_123"),
    ("AUTHORIZATION", "BEARER abc.def~+/==", "abc.def~+/=="),
    ("Authorization", " \tBearer  abc \t", "abc"),
])
def test_bearer_format_and_case(name, value, expected):
    assert bearer_token({name: value}) == expected


@pytest.mark.parametrize("headers", [
    {}, {"Authorization": ""}, {"Authorization": None},
    {"Authorization": "Basic abc"}, {"Authorization": "Bearer"},
    {"Authorization": "Bearer "}, {"Authorization": "Bearer a b"},
    {"Authorization": "Bearer\tabc"}, {"Authorization": "Bearer токен"},
    {"Authorization": "Bearer abc\n"}, {"Authorization": "Bearer abc,def"},
    {"Authorization": "Bearer abc=def"},
    {"Authorization": "Bearer a", "authorization": "Bearer b"},
    {"X-User-Id": "user-a"},
])
def test_missing_or_invalid_header_is_401_without_lookup(headers, sessions):
    request = Request("GET", "/api/profile", headers=headers)
    with pytest.raises(HttpError) as caught:
        authenticate_request(request, sessions, lambda: NOW)
    assert caught.value.status == 401
    assert caught.value.code == "unauthorized"
    sessions.get_by_token.assert_not_called()


def test_session_lookup_returns_verified_id(sessions):
    request = Request("GET", "/api/profile", headers={
        "Authorization": "Bearer Exact_Case",
    })
    authenticate = make_authenticator(sessions, lambda: NOW)
    assert authenticate(request) == "user-a"
    sessions.get_by_token.assert_called_once_with("Exact_Case")


def test_unknown_token_is_401(sessions):
    sessions.get_by_token.return_value = None
    with pytest.raises(HttpError) as caught:
        authenticate_request(Request("GET", "/api/profile", headers={
            "Authorization": "Bearer unknown",
        }), sessions, lambda: NOW)
    assert caught.value.status == 401


@pytest.mark.parametrize("expires", [NOW, NOW - timedelta(microseconds=1)])
def test_expired_or_exact_expiry_is_401(sessions, expires):
    sessions.get_by_token.return_value.expires_at = expires
    with pytest.raises(HttpError) as caught:
        authenticate_request(Request("GET", "/api/profile", headers={
            "Authorization": "Bearer existing",
        }), sessions, lambda: NOW)
    assert caught.value.status == 401


@pytest.mark.parametrize("expires, clock_value, valid", [
    (NOW.replace(tzinfo=None) + timedelta(seconds=1), NOW, True),
    (NOW.replace(tzinfo=None), NOW, False),
    (NOW + timedelta(seconds=1), NOW.replace(tzinfo=None), True),
    (NOW.astimezone(timezone(timedelta(hours=5))), NOW, False),
    ((NOW + timedelta(seconds=1)).astimezone(
        timezone(timedelta(hours=5))), NOW, True),
])
def test_expiry_is_compared_as_utc(sessions, expires, clock_value, valid):
    sessions.get_by_token.return_value.expires_at = expires
    request = Request("GET", "/api/profile", headers={
        "Authorization": "Bearer existing",
    })
    if valid:
        assert authenticate_request(
            request, sessions, lambda: clock_value,
        ) == "user-a"
    else:
        with pytest.raises(HttpError):
            authenticate_request(request, sessions, lambda: clock_value)


@pytest.mark.parametrize("user_id, expires", [
    ("", NOW), (None, NOW), (" ", NOW), (123, NOW),
    ("user-a", None), ("user-a", "2026-10-21"),
])
def test_incomplete_session_cannot_authorize(sessions, user_id, expires):
    sessions.get_by_token.return_value = SimpleNamespace(
        user_id=user_id, expires_at=expires,
    )
    with pytest.raises(HttpError):
        authenticate_request(Request("GET", "/api/profile", headers={
            "Authorization": "Bearer existing",
        }), sessions, lambda: NOW)


@pytest.mark.parametrize("method, path", sorted(PUBLIC_ROUTES))
@pytest.mark.parametrize("headers", [{}, {"Authorization": "invalid"}])
def test_public_routes_do_not_lookup_session(method, path, headers, sessions):
    assert authenticate_request(
        Request(method, path, headers=headers), sessions,
        Mock(side_effect=AssertionError("Часы не нужны")),
    ) is None
    sessions.get_by_token.assert_not_called()


@pytest.mark.parametrize("method, path", [
    ("POST", "/api/health"), ("GET", "/api/auth/login"),
    ("POST", "/api/auth/login/"), ("GET", "/api/health/private"),
    ("POST", "/api/auth/logout"),
])
def test_allowlist_does_not_include_other_methods_or_prefixes(method, path):
    with pytest.raises(HttpError):
        authenticate_request(Request(method, path))


def test_missing_repository_never_accepts_token():
    request = Request("GET", "/api/profile", headers={
        "Authorization": "Bearer valid-looking-token",
    })
    with pytest.raises(RuntimeError, match="SessionRepository"):
        authenticate_request(request)


def test_repository_failure_propagates(sessions):
    sessions.get_by_token.side_effect = RuntimeError("Storage unavailable")
    with pytest.raises(RuntimeError, match="Storage unavailable"):
        authenticate_request(Request("GET", "/api/profile", headers={
            "Authorization": "Bearer existing",
        }), sessions)


def test_default_clock_uses_actual_utc(sessions):
    sessions.get_by_token.return_value.expires_at = datetime.max.replace(
        tzinfo=timezone.utc,
    )
    assert authenticate_request(Request("GET", "/api/profile", headers={
        "Authorization": "Bearer existing",
    }), sessions) == "user-a"


def test_bad_clock_does_not_authorize(sessions):
    with pytest.raises(TypeError):
        make_authenticator(sessions, NOW)
    with pytest.raises(TypeError):
        authenticate_request(Request("GET", "/api/profile", headers={
            "Authorization": "Bearer existing",
        }), sessions, lambda: None)


def test_dispatch_passes_user_id_and_does_not_trust_existing_context(sessions):
    router = Router()
    handler = Mock(side_effect=lambda request: json_response(
        200, {"user_id": request.user_id},
    ))
    router.get("/api/profile", handler)
    request = Request("GET", "/api/profile", headers={
        "Authorization": "Bearer existing", "X-User-Id": "foreign",
    }, query={"user_id": "foreign"}, body=b'{"user_id":"foreign"}')
    request.user_id = "foreign"
    response = dispatch(
        router, request, make_authenticator(sessions, lambda: NOW),
    )
    assert response.payload == {"user_id": "user-a"}
    handler.assert_called_once_with(request)
    sessions.get_by_token.assert_called_once_with("existing")

    request.headers = {}
    assert dispatch(router, request).status == 401
    assert request.user_id is None
    assert handler.call_count == 1


def test_public_request_has_no_stale_user_id():
    request = Request("GET", "/api/health")
    request.user_id = "stale"
    router = Router()
    router.get("/api/health", lambda r: json_response(200, r.user_id))
    assert dispatch(router, request).status == 200
    assert request.user_id is None
    with pytest.raises(TypeError):
        Request("GET", "/api/profile", user_id="unverified")
