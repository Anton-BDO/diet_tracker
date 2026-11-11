"""Обработчики профиля пользователя."""
from backend.api.http_utils import json_response
from backend.api.serializers import user_to_public


def make_get_profile_handler(profile_service):
    """Создать обработчик GET /api/profile."""

    def get_profile(request):
        user, norm = profile_service.get_profile(request.user_id)
        return json_response(200, user_to_public(user, norm))

    return get_profile


def make_update_profile_handler(profile_service):
    """Создать обработчик PATCH /api/profile."""

    def update_profile(request):
        user, norm = profile_service.update_profile(
            request.user_id,
            request.json(),
        )
        return json_response(200, user_to_public(user, norm))

    return update_profile
