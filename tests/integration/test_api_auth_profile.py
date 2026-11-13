"""Сквозные HTTP-тесты регистрации, входа, выхода и профиля."""
import threading

import pytest

from backend.app import build_server
from backend.config import load_settings
from backend.domain.models import User, age_on
from backend.domain.nutrition import calculate_daily_targets


@pytest.fixture
def endpoint(mongo_client, static_dir):
    settings = load_settings({
        "HOST": "127.0.0.1",
        "PORT": "0",
        "STATIC_DIR": str(static_dir),
    })
    server = build_server(settings, mongo_client)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host, port = server.server_address
    yield f"http://{host}:{port}"
    server.shutdown()
    server.server_close()


VALID_REGISTER = {
    "email": "user@example.com",
    "password": "strongpassword123",
    "name": "Алексей",
    "sex": "male",
    "birth_date": "1996-03-15",
    "height_cm": 180,
    "weight_kg": 80,
    "activity": 1.55,
    "goal": "lose",
}


def _register(http, endpoint, **overrides):
    body = dict(VALID_REGISTER)
    body.update(overrides)
    return http(endpoint + "/api/auth/register", "POST", body=body)


def _expected_norm(payload):
    user = User(
        email=payload["email"],
        password_hash="x" * 20,
        name=payload["name"],
        sex=payload["sex"],
        birth_date=payload["birth_date"],
        height_cm=payload["height_cm"],
        weight_kg=payload["weight_kg"],
        activity=payload["activity"],
        goal=payload["goal"],
    )
    age = age_on(user.birth_date)
    return calculate_daily_targets(
        user.sex, user.weight_kg, user.height_cm, age,
        user.activity, user.goal,
    )


def test_register_returns_token_profile_and_norm(endpoint, http):
    status, _, body = _register(http, endpoint)

    assert status == 201
    assert isinstance(body["token"], str) and body["token"]
    profile = body["profile"]
    assert profile["email"] == "user@example.com"
    assert profile["norm"] == _expected_norm(VALID_REGISTER)
    assert "password_hash" not in profile
    assert "password" not in body


def test_register_duplicate_email_conflict(endpoint, http):
    _register(http, endpoint)
    status, _, body = _register(http, endpoint, name="Другой")

    assert status == 409
    assert body["error"]["code"] == "conflict"
    assert body["error"]["field"] == "email"


@pytest.mark.parametrize("field", list(VALID_REGISTER))
def test_register_missing_field_is_400(endpoint, http, field):
    body = dict(VALID_REGISTER)
    del body[field]

    status, _, response = http(
        endpoint + "/api/auth/register", "POST", body=body,
    )

    assert status == 400
    assert response["error"]["code"] == "validation_error"
    assert response["error"]["field"] == field


def test_register_short_password_is_400(endpoint, http):
    status, _, body = _register(http, endpoint, password="short")

    assert status == 400
    assert body["error"]["field"] == "password"


@pytest.mark.parametrize("email", [
    "bad@",
    "a@@b",
    "a b@example.com",
])
def test_register_malformed_email_is_400(endpoint, http, email):
    status, _, body = _register(http, endpoint, email=email)

    assert status == 400
    assert body["error"]["field"] == "email"


def test_register_invalid_profile_value_is_400(endpoint, http):
    status, _, body = _register(http, endpoint, height_cm=90)

    assert status == 400
    assert body["error"]["field"] == "height_cm"


def _login(http, endpoint, email="user@example.com",
           password="strongpassword123"):
    return http(
        endpoint + "/api/auth/login",
        "POST",
        body={"email": email, "password": password},
    )


def test_login_returns_only_token(endpoint, http):
    _register(http, endpoint)
    status, _, body = _login(http, endpoint)

    assert status == 200
    assert set(body) == {"token"}


@pytest.mark.parametrize("email,password", [
    ("nobody@example.com", "strongpassword123"),
    ("user@example.com", "wrong-password"),
])
def test_login_wrong_credentials_share_same_401(endpoint, http,
                                                email, password):
    _register(http, endpoint)

    missing = _login(http, endpoint, "nobody@example.com", "x" * 20)
    wrong = _login(http, endpoint, "user@example.com", "wrong-password")

    assert missing[0] == 401
    assert wrong[0] == 401
    assert missing[2] == wrong[2]


def test_profile_requires_token(endpoint, http):
    assert http(endpoint + "/api/profile")[0] == 401


def test_profile_with_token_returns_norm(endpoint, http):
    _register(http, endpoint)
    _, _, login_body = _login(http, endpoint)

    status, _, body = http(endpoint + "/api/profile", headers={
        "Authorization": "Bearer " + login_body["token"],
    })

    assert status == 200
    assert body["email"] == "user@example.com"
    assert body["norm"] == _expected_norm(VALID_REGISTER)


def test_profile_unknown_token_is_401(endpoint, http):
    status, _, _ = http(endpoint + "/api/profile", headers={
        "Authorization": "Bearer unknown",
    })

    assert status == 401


@pytest.mark.parametrize("changes", [
    {"height_cm": 182},
    {"weight_kg": 79.5},
    {"activity": 1.725},
    {"goal": "keep"},
])
def test_patch_profile_updates_field_and_norm(endpoint, http, changes):
    _register(http, endpoint)
    _, _, login_body = _login(http, endpoint)
    headers = {"Authorization": "Bearer " + login_body["token"]}

    status, _, body = http(
        endpoint + "/api/profile", "PATCH", body=changes, headers=headers,
    )

    assert status == 200
    field = next(iter(changes))
    assert body[field] == changes[field]
    expected = dict(VALID_REGISTER)
    expected.update(changes)
    assert body["norm"] == _expected_norm(expected)


@pytest.mark.parametrize("changes", [
    {},
    {"email": "new@example.com"},
    {"birth_date": "1990-01-01"},
    {"height_cm": 90},
])
def test_patch_profile_invalid_changes_are_400(endpoint, http, changes):
    _register(http, endpoint)
    _, _, login_body = _login(http, endpoint)
    headers = {"Authorization": "Bearer " + login_body["token"]}

    status, _, body = http(
        endpoint + "/api/profile", "PATCH", body=changes, headers=headers,
    )

    assert status == 400
    assert body["error"]["code"] == "validation_error"


def test_logout_invalidates_token(endpoint, http):
    _register(http, endpoint)
    _, _, login_body = _login(http, endpoint)
    headers = {"Authorization": "Bearer " + login_body["token"]}

    status, _, body = http(endpoint + "/api/auth/logout", "POST",
                           headers=headers)

    assert status == 204
    assert body is None
    assert http(endpoint + "/api/profile", headers=headers)[0] == 401


def test_password_not_stored_in_plaintext(endpoint, http, mongo_client):
    _register(http, endpoint)

    document = mongo_client["diet_tracker"]["users"].find_one(
        {"email": "user@example.com"},
    )

    assert document["password_hash"] != VALID_REGISTER["password"]
    assert document["password_hash"].startswith("pbkdf2_sha256$")
