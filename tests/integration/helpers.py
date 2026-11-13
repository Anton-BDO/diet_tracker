"""Помощники интеграционных тестов API."""

REGISTER_PAYLOAD = {
    "email": "user@example.com",
    "password": "strongpassword123",
    "name": "Алексей",
    "sex": "male",
    "birth_date": "1996-03-15",
    "height_cm": 180,
    "weight_kg": 80,
    "activity": 1.55,
    "goal": "lose",
}


def auth_headers(http, endpoint, email="user@example.com"):
    """Зарегистрировать пользователя и вернуть заголовки с токеном."""
    payload = dict(REGISTER_PAYLOAD)
    payload["email"] = email
    status, _, body = http(
        endpoint + "/api/auth/register", "POST", body=payload,
    )
    assert status == 201, body
    return {"Authorization": "Bearer " + body["token"]}
