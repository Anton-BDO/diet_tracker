"""Репозиторий сессий авторизации."""

from backend.domain.models import Session
from backend.repositories._mapping import (
    session_from_document,
    session_to_document,
)


class SessionRepository:
    """Создаёт сессии и ищет их по токену."""

    def __init__(self, database):
        self._collection = database["sessions"]

    def create(self, session: Session) -> Session:
        """Сохранить сессию и вернуть модель с назначенным id."""
        if not isinstance(session, Session):
            raise TypeError("session must be a Session dataclass")

        document = session_to_document(session)
        document.pop("_id", None)
        result = self._collection.insert_one(document)
        session.id = str(result.inserted_id)
        return session

    def get_by_token(self, token: str) -> Session | None:
        """Найти сессию по точному значению токена."""
        if not isinstance(token, str) or not token:
            return None

        document = self._collection.find_one({"token": token})
        if document is None:
            return None
        return session_from_document(document)
