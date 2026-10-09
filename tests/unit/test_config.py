from backend.config import load_settings


def test_defaults():
    settings = load_settings({})
    assert settings.mongo_uri == "mongodb://localhost:27017"
    assert settings.db_name == "diet_tracker"
    assert settings.port == 8000
    assert settings.static_dir.endswith("frontend")


def test_reads_environment():
    settings = load_settings(
        {"MONGO_URI": "mongodb://mongo:27017", "PORT": "9000"}
    )
    assert settings.mongo_uri == "mongodb://mongo:27017"
    assert settings.port == 9000


def test_reads_os_environ_by_default(monkeypatch):
    monkeypatch.setenv("DB_NAME", "from_env")
    assert load_settings().db_name == "from_env"
