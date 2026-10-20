import shutil
from pathlib import Path

from backend.api.router import Router


def test_auth_page_and_es_modules_are_served_without_database(
    static_dir, run_server, http
):
    source = Path(__file__).resolve().parents[2] / "frontend"
    shutil.copytree(source, static_dir, dirs_exist_ok=True)
    base = run_server(Router())
    code, headers, html = http(f"{base}/")
    assert code == 200
    assert 'lang="ru"' in html
    assert 'src="/js/main.js"' in html
    for module in (
        "main.js", "api.js", "store.js", "auth-validation.js", "views/login.js"
    ):
        code, headers, content = http(f"{base}/js/{module}")
        assert code == 200
        assert "javascript" in headers["Content-Type"]
        assert content
