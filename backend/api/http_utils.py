"""Общие помощники HTTP-слоя: запрос, ответ, JSON, ошибки, CORS."""
import json
from dataclasses import dataclass, field
from typing import Any, Optional


class HttpError(Exception):
    """Ошибка, которую HTTP-слой отдаёт клиенту в едином формате."""

    def __init__(self, status, code, message, field_name=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.field = field_name


@dataclass
class Request:
    """Разобранный HTTP-запрос, который получает обработчик."""

    method: str
    path: str
    query: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    body: bytes = b""
    params: dict = field(default_factory=dict)

    def json(self):
        """Тело запроса как словарь."""
        return parse_json(self.body)


@dataclass
class Response:
    """Ответ обработчика: код, данные для JSON и доп. заголовки."""

    status: int
    payload: Optional[Any] = None
    headers: dict = field(default_factory=dict)

    def body_bytes(self):
        """Тело ответа в байтах, пустое если данных нет."""
        if self.payload is None:
            return b""
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")


def json_response(status, payload=None):
    """Ответ с JSON-телом."""
    return Response(status=status, payload=payload)


def error_payload(code, message, field_name=None):
    """Единый формат ошибки из спецификации API."""
    error = {"code": code, "message": message}
    if field_name:
        error["field"] = field_name
    return {"error": error}


def error_response(status, code, message, field_name=None):
    """Ответ с ошибкой в едином формате."""
    return json_response(status, error_payload(code, message, field_name))


def parse_json(body):
    """Разобрать тело запроса. Ожидается JSON-объект."""
    if not body:
        raise HttpError(400, "invalid_json", "Пустое тело запроса")
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HttpError(400, "invalid_json", "Тело запроса не JSON") from None
    if not isinstance(data, dict):
        raise HttpError(400, "invalid_json", "Ожидается JSON-объект")
    return data


def cors_headers(origin):
    """Заголовки CORS для любого ответа API."""
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "GET, POST, PATCH, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Max-Age": "600",
    }
