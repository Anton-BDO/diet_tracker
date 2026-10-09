"""Общие фикстуры: mongomock вместо базы и сервер в фоновом потоке."""
import json
import threading
import urllib.error
import urllib.request

import mongomock
import pytest

from backend.api.server import create_server

# Без прокси: запросы к 127.0.0.1 не должны уходить в системный прокси.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


@pytest.fixture
def mongo_client():
    return mongomock.MongoClient()


@pytest.fixture
def db(mongo_client):
    return mongo_client["diet_tracker_test"]


@pytest.fixture
def static_dir(tmp_path):
    (tmp_path / "index.html").write_text("<h1>ok</h1>", encoding="utf-8")
    return tmp_path


@pytest.fixture
def run_server(static_dir):
    """Запустить сервер с переданным роутером, вернуть базовый URL."""
    servers = []

    def _run(router):
        server = create_server(router, "127.0.0.1", 0, "*", str(static_dir))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        host, port = server.server_address
        return f"http://{host}:{port}"

    yield _run
    for server in servers:
        server.shutdown()
        server.server_close()


def _decode(raw):
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError:
        return raw.decode("utf-8")


@pytest.fixture
def http():
    """Сделать запрос через urllib: (код, заголовки, тело)."""

    def _request(url, method="GET", body=None, headers=None):
        if body is not None and not isinstance(body, bytes):
            body = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            url, data=body, method=method, headers=headers or {}
        )
        try:
            with _OPENER.open(request, timeout=5) as response:
                return (
                    response.status,
                    dict(response.headers),
                    _decode(response.read()),
                )
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), _decode(exc.read())

    return _request
