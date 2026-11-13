"""Точка входа: сборка зависимостей и запуск сервера.

Запуск: python -m backend.app
"""
import logging

from backend.api.auth import make_authenticator
from backend.api.handlers.auth import (
    make_login_handler,
    make_logout_handler,
    make_register_handler,
)
from backend.api.handlers.health import make_health_handler
from backend.api.handlers.profile import (
    make_get_profile_handler,
    make_update_profile_handler,
)
from backend.api.router import Router
from backend.api.server import create_server
from backend.config import load_settings
from backend.db import create_client, ensure_indexes, get_database

from backend.repositories import SessionRepository, UserRepository
from backend.services.auth import AuthService
from backend.services.profile import ProfileService


def build_router(client, users, sessions, clock=None):
    """Зарегистрировать все маршруты API с их сервисами."""
    router = Router()
    router.get(
        "/api/health",
        make_health_handler(lambda: client.admin.command("ping")),
    )

    auth_service = AuthService(users, sessions, clock=clock)
    profile_service = ProfileService(users)

    router.post(
        "/api/auth/register",
        make_register_handler(auth_service, profile_service),
    )
    router.post("/api/auth/login", make_login_handler(auth_service))
    router.post("/api/auth/logout", make_logout_handler(auth_service))
    router.get("/api/profile", make_get_profile_handler(profile_service))
    router.patch("/api/profile", make_update_profile_handler(profile_service))
    return router


def build_server(settings, client, *, session_repository=None, clock=None):
    """Подготовить базу и собрать сервер. В тестах client = mongomock."""
    db = get_database(client, settings.db_name)
    ensure_indexes(db)
    if session_repository is None:
        session_repository = SessionRepository(db)
    users = UserRepository(db)
    router = build_router(client, users, session_repository, clock=clock)
    return create_server(
        router,
        settings.host,
        settings.port,
        settings.cors_origin,
        settings.static_dir,
        authenticate=make_authenticator(session_repository, clock),
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
