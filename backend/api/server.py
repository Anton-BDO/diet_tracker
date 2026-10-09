"""HTTP-сервер на стандартной библиотеке: API и статика фронта."""
import logging
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from backend.api.http_utils import (
    HttpError,
    Request,
    Response,
    cors_headers,
    error_response,
)
from backend.domain.errors import ConflictError, NotFoundError, ValidationError

API_PREFIX = "/api"
logger = logging.getLogger(__name__)


def dispatch(router, request):
    """Вызвать обработчик и превратить любые ошибки в ответ."""
    try:
        handler, params = router.resolve(request.method, request.path)
        request.params = params
        return handler(request)
    except HttpError as exc:
        return error_response(exc.status, exc.code, exc.message, exc.field)
    except ValidationError as exc:
        return error_response(400, "validation_error", str(exc), exc.field)
    except NotFoundError as exc:
        return error_response(404, "not_found", str(exc))
    except ConflictError as exc:
        return error_response(409, "conflict", str(exc))
    except Exception:
        logger.exception("Ошибка в %s %s", request.method, request.path)
        return error_response(
            500, "internal_error", "Внутренняя ошибка сервера"
        )


def resolve_static(static_dir, url_path):
    """Вернуть путь к файлу фронта или None, не выходя за папку."""
    root = Path(static_dir).resolve()
    relative = url_path.lstrip("/") or "index.html"
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        return None
    return candidate


def make_handler(router, cors_origin, static_dir):
    """Собрать класс обработчика с нужными зависимостями."""

    class Handler(BaseHTTPRequestHandler):
        server_version = "DietTracker/0.1"

        def do_OPTIONS(self):
            self._send(Response(204))

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

        def do_PATCH(self):
            self._handle("PATCH")

        def do_DELETE(self):
            self._handle("DELETE")

        def _handle(self, method):
            parts = urlsplit(self.path)
            path = parts.path
            if path == API_PREFIX or path.startswith(API_PREFIX + "/"):
                request = self._build_request(method, parts)
                self._send(dispatch(router, request))
            elif method == "GET":
                self._send_static(path)
            else:
                self._send(error_response(404, "not_found", "Не найдено"))

        def _build_request(self, method, parts):
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = 0
            body = self.rfile.read(length) if length > 0 else b""
            query = {k: v[0] for k, v in parse_qs(parts.query).items()}
            return Request(
                method=method,
                path=parts.path,
                query=query,
                headers=dict(self.headers),
                body=body,
            )

        def _send_static(self, path):
            file_path = resolve_static(static_dir, path)
            if file_path is None:
                self._send(error_response(404, "not_found", "Не найдено"))
                return
            content = file_path.read_bytes()
            content_type = mimetypes.guess_type(file_path.name)[0]
            self.send_response(200)
            self.send_header(
                "Content-Type", content_type or "application/octet-stream"
            )
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def _send(self, response):
            body = response.body_bytes()
            headers = {**cors_headers(cors_origin), **response.headers}
            if body:
                headers["Content-Type"] = "application/json; charset=utf-8"
            headers["Content-Length"] = str(len(body))
            self.send_response(response.status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            if body:
                self.wfile.write(body)

        def log_message(self, fmt, *args):
            logger.info("%s %s", self.address_string(), fmt % args)

    return Handler


def create_server(router, host, port, cors_origin, static_dir):
    """Создать многопоточный HTTP-сервер."""
    handler = make_handler(router, cors_origin, static_dir)
    return ThreadingHTTPServer((host, port), handler)
