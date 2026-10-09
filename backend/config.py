"""Настройки приложения из переменных окружения."""
import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    """Все настройки сервера в одном месте."""

    mongo_uri: str
    db_name: str
    host: str
    port: int
    cors_origin: str
    static_dir: str


def load_settings(env=None):
    """Собрать настройки из окружения, подставив значения по умолчанию."""
    env = os.environ if env is None else env
    return Settings(
        mongo_uri=env.get("MONGO_URI", "mongodb://localhost:27017"),
        db_name=env.get("DB_NAME", "diet_tracker"),
        host=env.get("HOST", "0.0.0.0"),
        port=int(env.get("PORT", "8000")),
        cors_origin=env.get("CORS_ORIGIN", "*"),
        static_dir=env.get("STATIC_DIR", str(BASE_DIR / "frontend")),
    )
