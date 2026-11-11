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


def product_to_public(product):
    """Публичные поля продукта, id наружу строкой."""
    return {
        "id": product.id,
        "name": product.name,
        "kcal": product.kcal,
        "protein": product.protein,
        "fat": product.fat,
        "carbs": product.carbs,
        "owner_id": product.owner_id,
    }


def entry_to_public(entry):
    """Публичные поля записи дневника."""
    return {
        "id": entry.id,
        "product_id": entry.product_id,
        "product_name": entry.product_name,
        "date": entry.date,
        "meal": entry.meal,
        "grams": entry.grams,
        "kcal": entry.kcal,
        "protein": entry.protein,
        "fat": entry.fat,
        "carbs": entry.carbs,
    }


def weight_log_to_public(log):
    """Публичные поля замера веса."""
    return {
        "id": log.id,
        "date": log.date,
        "weight_kg": log.weight_kg,
    }
