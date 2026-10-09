"""Сквозные проверки сервера: настоящий HTTP через urllib."""
import pytest

from backend.api.http_utils import json_response
from backend.api.router import Router
from backend.app import build_router, build_server
from backend.config import load_settings
from backend.domain.errors import ConflictError, NotFoundError, ValidationError


def _raise(error):
    def handler(request):
        raise error

    return handler


@pytest.fixture
def base_url(run_server):
    router = Router()
    router.get(
        "/api/items/{item_id}",
        lambda r: json_response(200, {"id": r.params["item_id"], **r.query}),
    )
    router.post("/api/items", lambda r: json_response(201, r.json()))
    router.get("/api/invalid", _raise(ValidationError("Плохо", "grams")))
    router.get("/api/missing", _raise(NotFoundError("Нет такого")))
    router.get("/api/conflict", _raise(ConflictError("Занято")))
    router.get("/api/boom", _raise(RuntimeError("секрет")))
    return run_server(router)


def test_health_with_app_router(run_server, mongo_client, http):
    url = run_server(build_router(mongo_client))
    status, headers, body = http(url + "/api/health")
    assert status == 200
    assert body == {"status": "ok", "db": "ok"}
    assert headers["Content-Type"].startswith("application/json")
    assert headers["Access-Control-Allow-Origin"] == "*"


def test_path_and_query_params(base_url, http):
    status, _, body = http(base_url + "/api/items/42?date=2026-10-09")
    assert status == 200
    assert body == {"id": "42", "date": "2026-10-09"}


def test_post_json(base_url, http):
    status, _, body = http(base_url + "/api/items", "POST", {"grams": 150})
    assert status == 201
    assert body == {"grams": 150}


def test_post_bad_json(base_url, http):
    status, _, body = http(base_url + "/api/items", "POST", b"{oops")
    assert status == 400
    assert body["error"]["code"] == "invalid_json"


@pytest.mark.parametrize(
    "path, status, code",
    [
        ("/api/invalid", 400, "validation_error"),
        ("/api/missing", 404, "not_found"),
        ("/api/conflict", 409, "conflict"),
        ("/api/boom", 500, "internal_error"),
        ("/api/unknown", 404, "not_found"),
    ],
)
def test_errors_are_json(base_url, http, path, status, code):
    got_status, _, body = http(base_url + path)
    assert got_status == status
    assert body["error"]["code"] == code


def test_internal_error_hides_details(base_url, http):
    _, _, body = http(base_url + "/api/boom")
    assert "секрет" not in body["error"]["message"]


def test_validation_error_has_field(base_url, http):
    _, _, body = http(base_url + "/api/invalid")
    assert body["error"]["field"] == "grams"


def test_wrong_method_is_405(base_url, http):
    status, _, _ = http(base_url + "/api/items", "DELETE")
    assert status == 405


def test_patch_goes_to_router(base_url, http):
    status, _, _ = http(base_url + "/api/items", "PATCH", {"a": 1})
    assert status == 405


def test_options_preflight(base_url, http):
    status, headers, body = http(base_url + "/api/items", "OPTIONS")
    assert status == 204
    assert body is None
    assert "POST" in headers["Access-Control-Allow-Methods"]


def test_serves_index(base_url, http):
    status, headers, body = http(base_url + "/")
    assert status == 200
    assert headers["Content-Type"].startswith("text/html")
    assert body == "<h1>ok</h1>"


def test_static_missing_file(base_url, http):
    status, _, _ = http(base_url + "/nope.js")
    assert status == 404


def test_static_blocks_path_traversal(base_url, http):
    status, _, _ = http(base_url + "/../../etc/passwd")
    assert status == 404


def test_post_outside_api_is_404(base_url, http):
    status, _, _ = http(base_url + "/index.html", "POST", {"a": 1})
    assert status == 404


def test_build_server_creates_indexes(mongo_client, static_dir):
    settings = load_settings(
        {"HOST": "127.0.0.1", "PORT": "0", "STATIC_DIR": str(static_dir)}
    )
    server = build_server(settings, mongo_client)
    try:
        users = mongo_client[settings.db_name].users
        assert "email_1" in users.index_information()
    finally:
        server.server_close()
