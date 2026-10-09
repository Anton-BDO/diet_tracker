"""Ошибки бизнес-логики. HTTP-слой превращает их в коды ответа."""


class DomainError(Exception):
    """Базовая ошибка бизнес-логики."""


class ValidationError(DomainError):
    """Неверные входные данные, отдаётся как 400."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.field = field


class NotFoundError(DomainError):
    """Объект не найден или принадлежит другому пользователю, 404."""


class ConflictError(DomainError):
    """Конфликт данных, например email уже занят, 409."""
