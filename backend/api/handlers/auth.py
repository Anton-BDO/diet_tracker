"""Обработчики регистрации, входа и выхода."""
from backend.api.auth import bearer_token
from backend.api.http_utils import json_response
from backend.api.serializers import user_to_public


def make_register_handler(auth_service, profile_service):
    """Создать обработчик POST /api/auth/register."""

    def register(request):
        data = request.json()
        token, user = auth_service.register(data)
        norm = profile_service.norm_for(user)
        return json_response(201, {
            "token": token,
            "profile": user_to_public(user, norm),
        })

    return register


def make_login_handler(auth_service):
    """Создать обработчик POST /api/auth/login."""

    def login(request):
        data = request.json()
        token = auth_service.login(data.get("email"), data.get("password"))
        return json_response(200, {"token": token})

    return login


def make_logout_handler(auth_service):
    """Создать обработчик POST /api/auth/logout."""

    def logout(request):
        auth_service.logout(bearer_token(request.headers))
        return json_response(204)

    return logout
