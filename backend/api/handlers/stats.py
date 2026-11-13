"""Обработчики статистики калорий."""
from backend.api.http_utils import json_response


def make_get_calories_stats_handler(stats_service):
    """Создать обработчик GET /api/stats/calories?days=&today=."""

    def get_calories_stats(request):
        result = stats_service.get_calories(
            request.query.get("days"),
            request.query.get("today"),
            request.user_id,
        )
        return json_response(200, result)

    return get_calories_stats
