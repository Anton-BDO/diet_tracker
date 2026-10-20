"""Проверка Bearer-сессии до вызова обработчика, без доступа к MongoDB."""
from datetime import datetime, timezone
import re
from typing import Optional, Protocol

from backend.api.http_utils import HttpError

PUBLIC_ROUTES = frozenset({
    ("GET", "/api/health"),
    ("POST", "/api/auth/register"),
    ("POST", "/api/auth/login"),
})
_BEARER = re.compile(
    r"Bearer +([A-Za-z0-9._~+/-]+=*)", re.IGNORECASE | re.ASCII,
)


class SessionRecord(Protocol):
    """Используемые поля доменной сессии; id уже преобразован репозиторием."""

    user_id: str
    expires_at: datetime


class SessionRepository(Protocol):
    """Требуемый интерфейс общего репозитория, без реализации хранения."""

    def get_by_token(self, token: str) -> Optional[SessionRecord]:
        """Вернуть сессию по точному токену или None."""
        ...


def _unauthorized():
    return HttpError(
        401, "unauthorized", "Требуется действующая Bearer-сессия",
    )


def bearer_token(headers):
    """Извлечь единственный токен; имя заголовка и схема без учёта регистра.

    HTTP допускает внешние пробелы и несколько SP после схемы. Внутри
    токена пробелы, запятые, управляющие и не-ASCII символы запрещены.
    """
    values = [value for name, value in headers.items()
              if name.lower() == "authorization"]
    if len(values) != 1 or not isinstance(values[0], str):
        raise _unauthorized()
    match = _BEARER.fullmatch(values[0].strip(" \t"))
    if match is None:
        raise _unauthorized()
    return match.group(1)


def _utc(value):
    """BSON datetime без tzinfo означает UTC, не часовой пояс сервера."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def authenticate_request(request, session_repository=None, clock=None):
    """Вернуть проверенный user_id или None для точных публичных маршрутов.

    Существование и срок сессии проверяются на каждом запросе. Источник
    времени возвращает datetime UTC (naive UTC тоже допустим). Проблема
    хранилища не маскируется под неверный токен и не разрешает доступ.
    """
    if (request.method.upper(), request.path) in PUBLIC_ROUTES:
        return None
    token = bearer_token(request.headers)
    if session_repository is None:
        raise RuntimeError("Не настроен SessionRepository для Bearer-проверки")
    session = session_repository.get_by_token(token)
    if session is None:
        raise _unauthorized()
    user_id = getattr(session, "user_id", None)
    expires_at = getattr(session, "expires_at", None)
    if (not isinstance(user_id, str) or not user_id.strip()
            or not isinstance(expires_at, datetime)):
        raise _unauthorized()
    now = clock() if clock is not None else datetime.now(timezone.utc)
    if not isinstance(now, datetime):
        raise TypeError("Источник времени должен возвращать datetime")
    if _utc(expires_at) <= _utc(now):
        raise _unauthorized()
    return user_id


def make_authenticator(session_repository: Optional[SessionRepository],
                       clock=None):
    """Связать настоящий репозиторий и часы при сборке приложения."""
    if clock is not None and not callable(clock):
        raise TypeError("Источник времени должен быть вызываемым объектом")

    def authenticate(request):
        return authenticate_request(request, session_repository, clock)

    return authenticate
