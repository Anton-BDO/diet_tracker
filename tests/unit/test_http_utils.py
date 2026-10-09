import pytest

from backend.api.http_utils import (
    HttpError,
    Request,
    Response,
    cors_headers,
    error_payload,
    parse_json,
)


def test_parse_json_object():
    assert parse_json(b'{"grams": 150}') == {"grams": 150}


@pytest.mark.parametrize(
    "body", [b"", b"not json", b"[1, 2]", b"\xff\xfe"]
)
def test_parse_json_rejects_bad_body(body):
    with pytest.raises(HttpError) as exc:
        parse_json(body)
    assert exc.value.status == 400
    assert exc.value.code == "invalid_json"


def test_request_json_reads_body():
    request = Request(method="POST", path="/api/x", body=b'{"a": 1}')
    assert request.json() == {"a": 1}


def test_error_payload_with_field():
    payload = error_payload("validation_error", "Плохой рост", "height_cm")
    assert payload == {
        "error": {
            "code": "validation_error",
            "message": "Плохой рост",
            "field": "height_cm",
        }
    }


def test_error_payload_without_field():
    assert "field" not in error_payload("not_found", "Нет")["error"]


def test_response_body_bytes():
    assert Response(204).body_bytes() == b""
    assert Response(200, {"x": "ё"}).body_bytes() == '{"x": "ё"}'.encode()


def test_cors_headers_use_origin():
    headers = cors_headers("http://localhost:5500")
    assert headers["Access-Control-Allow-Origin"] == "http://localhost:5500"
    assert "Authorization" in headers["Access-Control-Allow-Headers"]
