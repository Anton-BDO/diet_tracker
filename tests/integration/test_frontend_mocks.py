import shutil
from pathlib import Path

from backend.api.router import Router


def test_frontend_server_serves_mock_data_without_database(
    static_dir, run_server, http
):
    source = Path(__file__).resolve().parents[2] / "frontend/js/mocks"
    shutil.copytree(source, static_dir / "js/mocks")
    base = run_server(Router())
    code, headers, data = http(f"{base}/js/mocks/data/day-summary.json")
    assert code == 200
    assert "application/json" in headers["Content-Type"]
    assert data["eaten_calories"] == 2063.0
    assert data["streak"] == {"current": 4, "record": 7}

    code, headers, source_text = http(f"{base}/js/mocks/index.js")
    assert code == 200
    assert "javascript" in headers["Content-Type"]
    assert "export async function mockRequest" in source_text
