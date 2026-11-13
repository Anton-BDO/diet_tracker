"""Обработчики серий успешных дней."""
from backend.api.http_utils import json_response


def make_get_streak_handler(streak_service):
    """Создать обработчик GET /api/streak?today=."""

    def get_streak(request):
        result = streak_service.get_streak(
            request.query.get("today"),
            request.user_id,
        )
        return json_response(200, result)

    return get_streak
