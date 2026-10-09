import pytest

from backend.api.http_utils import HttpError
from backend.api.router import Router


def handler(request):
    return "ok"


def test_resolves_static_path():
    router = Router()
    router.get("/api/health", handler)
    found, params = router.resolve("GET", "/api/health")
    assert found is handler
    assert params == {}


def test_extracts_path_params():
    router = Router()
    router.delete("/api/diary/{entry_id}", handler)
    _, params = router.resolve("delete", "/api/diary/abc123")
    assert params == {"entry_id": "abc123"}


def test_param_does_not_match_nested_path():
    router = Router()
    router.get("/api/diary/{entry_id}", handler)
    with pytest.raises(HttpError) as exc:
        router.resolve("GET", "/api/diary/a/b")
    assert exc.value.status == 404


def test_dot_in_pattern_is_literal():
    router = Router()
    router.get("/api/file.json", handler)
    with pytest.raises(HttpError):
        router.resolve("GET", "/api/fileXjson")


def test_unknown_path_is_404():
    with pytest.raises(HttpError) as exc:
        Router().resolve("GET", "/api/nope")
    assert exc.value.status == 404
    assert exc.value.code == "not_found"


def test_wrong_method_is_405():
    router = Router()
    router.post("/api/products", handler)
    router.patch("/api/profile", handler)
    with pytest.raises(HttpError) as exc:
        router.resolve("GET", "/api/products")
    assert exc.value.status == 405
