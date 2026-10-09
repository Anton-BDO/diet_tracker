"""Простой роутер: метод и шаблон пути -> функция-обработчик."""
import re

from backend.api.http_utils import HttpError

_PARAM = re.compile(r"\{(\w+)\}")


def _compile(pattern):
    """Превратить '/api/diary/{entry_id}' в регулярное выражение."""
    parts = []
    pos = 0
    for match in _PARAM.finditer(pattern):
        parts.append(re.escape(pattern[pos:match.start()]))
        parts.append(f"(?P<{match.group(1)}>[^/]+)")
        pos = match.end()
    parts.append(re.escape(pattern[pos:]))
    return re.compile("^" + "".join(parts) + "$")


class Router:
    """Таблица маршрутов. Обработчик получает Request, отдаёт Response."""

    def __init__(self):
        self._routes = []

    def add(self, method, pattern, handler):
        """Зарегистрировать обработчик для метода и шаблона пути."""
        self._routes.append((method.upper(), _compile(pattern), handler))

    def get(self, pattern, handler):
        self.add("GET", pattern, handler)

    def post(self, pattern, handler):
        self.add("POST", pattern, handler)

    def patch(self, pattern, handler):
        self.add("PATCH", pattern, handler)

    def delete(self, pattern, handler):
        self.add("DELETE", pattern, handler)

    def resolve(self, method, path):
        """Найти обработчик и параметры пути или бросить 404/405."""
        path_matched = False
        for route_method, regex, handler in self._routes:
            match = regex.match(path)
            if match is None:
                continue
            if route_method == method.upper():
                return handler, match.groupdict()
            path_matched = True
        if path_matched:
            raise HttpError(
                405, "method_not_allowed", "Метод не поддерживается"
            )
        raise HttpError(404, "not_found", "Ресурс не найден")
