from backend.api.handlers.health import make_health_handler


def test_health_ok():
    response = make_health_handler(lambda: None)(None)
    assert response.status == 200
    assert response.payload == {"status": "ok", "db": "ok"}


def test_health_db_down():
    def broken():
        raise ConnectionError("нет базы")

    response = make_health_handler(broken)(None)
    assert response.status == 503
    assert response.payload["db"] == "down"
