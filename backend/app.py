"""Точка входа: сборка зависимостей и запуск сервера.

Запуск: python -m backend.app
"""
import logging

from backend.api.handlers.health import make_health_handler
from backend.api.router import Router
from backend.api.server import create_server
from backend.config import load_settings
from backend.db import create_client, ensure_indexes, get_database


def build_router(client):
    """Зарегистрировать все маршруты API.

    Сюда же подключаются сервисы и репозитории по мере готовности.
    """
    router = Router()
    router.get(
        "/api/health",
        make_health_handler(lambda: client.admin.command("ping")),
    )
    return router


def build_server(settings, client):
    """Подготовить базу и собрать сервер. В тестах client = mongomock."""
    db = get_database(client, settings.db_name)
    ensure_indexes(db)
    router = build_router(client)
    return create_server(
        router,
        settings.host,
        settings.port,
        settings.cors_origin,
        settings.static_dir,
    )


def main():  # pragma: no cover
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    settings = load_settings()
    client = create_client(settings.mongo_uri)
    server = build_server(settings, client)
    logging.info("Сервер на http://%s:%s", settings.host, settings.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        client.close()


if __name__ == "__main__":  # pragma: no cover
    main()
