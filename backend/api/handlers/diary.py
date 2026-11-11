"""Обработчики дневника питания."""
from backend.api.http_utils import json_response
from backend.api.serializers import entry_to_public


def make_create_entry_handler(diary_service):
    """Создать обработчик POST /api/diary."""

    def create_entry(request):
        entry = diary_service.create_entry(request.json(), request.user_id)
        return json_response(201, entry_to_public(entry))

    return create_entry


def make_get_day_handler(diary_service):
    """Создать обработчик GET /api/diary?date=."""

    def get_day(request):
        day = diary_service.get_day(request.query.get("date"), request.user_id)
        payload = dict(day)
        payload["entries"] = [
            entry_to_public(entry) for entry in day["entries"]
        ]
        return json_response(200, payload)

    return get_day


def make_update_entry_handler(diary_service):
    """Создать обработчик PATCH /api/diary/{id}."""

    def update_entry(request):
        entry = diary_service.update_entry(
            request.params["id"],
            request.json(),
            request.user_id,
        )
        return json_response(200, entry_to_public(entry))

    return update_entry


def make_delete_entry_handler(diary_service):
    """Создать обработчик DELETE /api/diary/{id}."""

    def delete_entry(request):
        diary_service.delete_entry(request.params["id"], request.user_id)
        return json_response(204)

    return delete_entry
