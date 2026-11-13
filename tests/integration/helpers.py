"""Помощники интеграционных тестов API."""

from backend.domain.models import User, age_on
from backend.domain.nutrition import calculate_daily_targets

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


def expected_norm():
    """Норма пользователя с данными REGISTER_PAYLOAD на сегодня.

    Возраст считается на текущую дату, поэтому эталон никогда не
    привязан к конкретному числу и тесты не ломаются со временем.
    """
    payload = REGISTER_PAYLOAD
    user = User(
        email=payload["email"],
        password_hash="x" * 20,
        name=payload["name"],
        sex=payload["sex"],
        birth_date=payload["birth_date"],
        height_cm=payload["height_cm"],
        weight_kg=payload["weight_kg"],
        activity=payload["activity"],
        goal=payload["goal"],
    )
    age = age_on(user.birth_date)
    return calculate_daily_targets(
        user.sex,
        user.weight_kg,
        user.height_cm,
        age,
        user.activity,
        user.goal,
    )
