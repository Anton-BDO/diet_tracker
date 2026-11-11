"""Преобразование моделей в публичные ответы API."""


def user_to_public(user, norm):
    """Публичный профиль: без пароля, хеша и служебных дат."""
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "sex": user.sex,
        "birth_date": user.birth_date,
        "height_cm": user.height_cm,
        "weight_kg": user.weight_kg,
        "activity": user.activity,
        "goal": user.goal,
        "norm": norm,
    }
