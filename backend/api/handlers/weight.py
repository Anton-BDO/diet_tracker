"""Обработчики журнала веса."""
from backend.api.http_utils import json_response
from backend.api.serializers import weight_log_to_public


def make_get_weight_history_handler(weight_service):
    """Создать обработчик GET /api/weight?from=&to=."""

    def get_history(request):
        logs = weight_service.get_history(
            request.user_id,
            request.query.get("from"),
            request.query.get("to"),
        )
        return json_response(200, [
            weight_log_to_public(log) for log in logs
        ])

    return get_history


def make_log_weight_handler(weight_service):
    """Создать обработчик POST /api/weight."""

    def log_weight(request):
        log = weight_service.log_weight(request.json(), request.user_id)
        return json_response(201, weight_log_to_public(log))

    return log_weight
