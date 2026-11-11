"""Сквозная проверка API на реальном Docker Compose.

Изолированный запуск (отдельный проект и база, volume потом удаляется):

    DB_NAME=diet_tracker_e2e docker compose -p diet-tracker-e2e \
        up --build -d
    python scripts/e2e_smoke.py
    docker compose -p diet-tracker-e2e down -v

Скрипт ждёт готовности app до 60 секунд, поэтому запускать можно
сразу после `docker compose up -d`, не дожидаясь вручную.

Каждый прогон регистрирует пользователей со случайными email. Прогон
всё равно оставляет данные в базе, поэтому против рабочей БД
(DB_NAME=diet_tracker) запускать не следует — только против
изолированной БД приведённой выше командой.

Сценарий повторяет раздел «Полный Docker E2E» рабочего гайда backend.
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000")

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

PASSED = []


def check(name, condition, details=""):
    """Зафиксировать шаг сценария; при провале вывести детали."""
    if not condition:
        raise SystemExit(f"FAIL: {name} {_safe(details)}")
    PASSED.append(name)
    print(f"ok: {name}")


def _safe(value):
    """Скрыть токены перед выводом в диагностику."""
    if isinstance(value, dict):
        return {
            key: "<hidden>" if key == "token" else item
            for key, item in value.items()
        }
    return value


def request(path, method="GET", body=None, token=None):
    """Выполнить запрос и вернуть (код, распарсенное тело)."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        BASE_URL + path, data=data, method=method, headers=headers,
    )
    try:
        with _OPENER.open(req, timeout=10) as response:
            return response.status, _decode(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, _decode(exc.read())


def _decode(raw):
    if not raw:
        return None
    return json.loads(raw.decode("utf-8"))


def wait_for_app(timeout_s=60):
    """Дождаться /api/health, пока app стартует после compose up."""
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            status, body = request("/api/health")
            if (status == 200 and isinstance(body, dict)
                    and body.get("db") == "ok"):
                return
        except (urllib.error.URLError, OSError):
            pass
        if time.monotonic() >= deadline:
            raise SystemExit(
                f"Сервер на {BASE_URL} не поднялся за {timeout_s} секунд"
            )
        time.sleep(1)


def _register(email):
    """Зарегистрировать пользователя и вернуть токен."""
    status, body = request("/api/auth/register", "POST", {
        "email": email,
        "password": "e2e-password-123",
        "name": "E2E",
        "sex": "male",
        "birth_date": "1996-03-15",
        "height_cm": 180,
        "weight_kg": 80,
        "activity": 1.55,
        "goal": "lose",
    })
    check(f"register {email}", status == 201, body)
    token = (body or {}).get("token")
    check("register returns token", bool(token), body)
    return token


def main():
    """Пройти сценарий регистрации до выхода и проверить изоляцию."""
    wait_for_app()

    email = f"e2e-{uuid.uuid4().hex[:12]}@example.com"
    password = "e2e-password-123"

    token = _register(email)

    status, body = request("/api/profile", token=token)
    check("profile 200", status == 200, body)
    norm_before = body["norm"]

    status, body = request("/api/auth/register", "POST", {
        "email": email,
        "password": password,
        "name": "E2E",
        "sex": "male",
        "birth_date": "1996-03-15",
        "height_cm": 180,
        "weight_kg": 80,
        "activity": 1.55,
        "goal": "lose",
    })
    check("duplicate register 409",
          status == 409 and body["error"]["field"] == "email", body)

    status, body = request("/api/auth/login", "POST", {
        "email": email, "password": "wrong-password",
    })
    check("wrong login 401", status == 401, body)

    status, body = request("/api/auth/login", "POST", {
        "email": email, "password": password,
    })
    check("login 200", status == 200 and set(body) == {"token"}, body)

    status, body = request("/api/profile", "PATCH",
                           {"weight_kg": 75}, token=token)
    check("patch profile 200", status == 200, body)
    check("norm recalculated",
          body["norm"]["kcal"] != norm_before["kcal"], body["norm"])

    product = {"name": "E2E Продукт", "kcal": 100, "protein": 10,
               "fat": 5, "carbs": 50}
    status, body = request("/api/products", "POST", product, token=token)
    check("create product 201", status == 201 and bool(body["id"]), body)
    product_id = body["id"]

    status, body = request(
        f"/api/products?q={urllib.parse.quote('e2e')}", token=token,
    )
    check("search product 200",
          status == 200
          and any(p["id"] == product_id for p in body), body)

    entry = {"product_id": product_id, "grams": 250, "meal": "lunch",
             "date": "2026-10-19"}
    status, body = request("/api/diary", "POST", entry, token=token)
    check("create diary entry 201",
          status == 201 and body["kcal"] == 250.0, body)
    entry_id = body["id"]

    status, body = request("/api/diary?date=2026-10-19", token=token)
    check("get diary 200",
          status == 200 and body["totals"]["kcal"] == 250.0, body)

    status, body = request(f"/api/diary/{entry_id}", "PATCH",
                           {"grams": 200}, token=token)
    check("patch diary 200",
          status == 200 and body["kcal"] == 200.0, body)

    status, body = request("/api/weight", "POST",
                           {"weight_kg": 75, "date": "2026-10-19"},
                           token=token)
    check("log weight 201", status == 201, body)

    status, body = request("/api/weight", "POST",
                           {"weight_kg": 74.5, "date": "2026-10-19"},
                           token=token)
    check("repeat weight same date 201", status == 201
          and body["weight_kg"] == 74.5, body)

    status, body = request("/api/weight", token=token)
    check("weight history 200",
          status == 200 and len(body) == 1 and body[0]["weight_kg"] == 74.5,
          body)

    status, body = request("/api/streak?today=2026-10-20", token=token)
    check("streak 200", status == 200
          and set(body) == {"current", "record"}, body)

    status, body = request(
        "/api/stats/calories?days=7&today=2026-10-20", token=token,
    )
    check("stats 200", status == 200
          and len(body["days"]) == 7 and body["norm_kcal"] > 0, body)

    # Запись для проверок изоляции: пользователь B будет пытаться
    # читать и менять её, а в конце она удаляется владельцем.
    iso_entry = {"product_id": product_id, "grams": 100, "meal": "snack",
                 "date": "2026-10-20"}
    status, body = request("/api/diary", "POST", iso_entry, token=token)
    check("create isolation entry 201", status == 201, body)
    iso_entry_id = body["id"]

    _check_isolation(product_id, iso_entry_id)

    status, body = request(f"/api/diary/{iso_entry_id}", "DELETE",
                           token=token)
    check("delete isolation entry 204", status == 204, body)

    status, _ = request(f"/api/diary/{entry_id}", "DELETE", token=token)
    check("delete diary entry 204", status == 204)

    status, _ = request("/api/auth/logout", "POST", token=token)
    check("logout 204", status == 204)

    status, _ = request("/api/profile", token=token)
    check("old token rejected 401", status == 401)

    print(f"\nPASSED: {len(PASSED)} checks")


def _check_isolation(product_id, iso_entry_id):
    """Второй пользователь не видит и не трогает данные первого."""
    token_b = _register(f"e2e-{uuid.uuid4().hex[:12]}@example.com")

    status, body = request("/api/products", token=token_b)
    check("isolation: foreign product hidden",
          status == 200
          and all(p["id"] != product_id for p in body), body)

    status, _ = request("/api/diary", "POST",
                        {"product_id": product_id, "grams": 100,
                         "meal": "snack", "date": "2026-10-19"},
                        token=token_b)
    check("isolation: cannot use foreign product", status == 404)

    target = f"/api/diary/{iso_entry_id}"
    status, _ = request(target, "PATCH", {"grams": 50}, token=token_b)
    check("isolation: cannot patch foreign entry", status == 404)
    status, _ = request(target, "DELETE", token=token_b)
    check("isolation: cannot delete foreign entry", status == 404)

    status, body = request("/api/weight", token=token_b)
    check("isolation: weight history empty",
          status == 200 and body == [], body)

    status, body = request("/api/streak?today=2026-10-20", token=token_b)
    check("isolation: streak is zero",
          status == 200
          and body == {"current": 0, "record": 0}, body)

    status, body = request(
        "/api/stats/calories?days=3&today=2026-10-20", token=token_b,
    )
    check("isolation: stats are zero",
          status == 200
          and all(day["kcal"] == 0 for day in body["days"]), body)


if __name__ == "__main__":
    main()
