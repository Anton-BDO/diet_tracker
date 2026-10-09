"""GET /api/health: сервер жив и видит базу."""
from backend.api.http_utils import json_response


def make_health_handler(check_db):
    """check_db бросает исключение, если база недоступна."""

    def health(request):
        try:
            check_db()
        except Exception:
            return json_response(503, {"status": "degraded", "db": "down"})
        return json_response(200, {"status": "ok", "db": "ok"})

    return health
