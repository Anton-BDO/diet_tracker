"""Преобразования BSON и доменных моделей."""

from bson import ObjectId

from backend.domain.models import FoodEntry, MacroTargets, Product, User


def parse_object_id(value):
    """Преобразовать идентификатор в ObjectId или вернуть None."""
    if isinstance(value, ObjectId):
        return value
    if not isinstance(value, str) or not ObjectId.is_valid(value):
        return None
    return ObjectId(value)


def user_to_document(user: User) -> dict:
    """Подготовить пользователя к сохранению."""
    document = {
        "email": user.email.strip().lower(),
        "password_hash": user.password_hash,
        "name": user.name,
        "gender": user.gender,
        "age": user.age,
        "height_cm": float(user.height_cm),
        "weight_kg": float(user.weight_kg),
        "activity": user.activity,
        "goal": user.goal,
        "daily_calories": user.daily_calories,
        "macros": {
            "protein": float(user.macros.protein),
            "fat": float(user.macros.fat),
            "carbs": float(user.macros.carbs),
        },
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }

    if user.id is not None:
        object_id = parse_object_id(user.id)
        if object_id is None:
            raise ValueError(
                "user.id must be a valid MongoDB ObjectId"
            )
        document["_id"] = object_id

    return document


def user_from_document(document: dict) -> User:
    """Преобразовать документ в пользователя."""
    return User(
        id=str(document["_id"]),
        email=document["email"],
        password_hash=document["password_hash"],
        name=document["name"],
        gender=document["gender"],
        age=document["age"],
        height_cm=document["height_cm"],
        weight_kg=document["weight_kg"],
        activity=document["activity"],
        goal=document["goal"],
        daily_calories=document["daily_calories"],
        macros=MacroTargets(**document["macros"]),
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def product_to_document(product: Product) -> dict:
    """Подготовить продукт для сохранения в MongoDB."""
    owner_id = None

    if product.owner_id is not None:
        owner_id = parse_object_id(product.owner_id)
        if owner_id is None:
            raise ValueError(
                "product.owner_id must be a valid MongoDB ObjectId"
            )

    document = {
        "name": product.name,
        "name_lower": product.name_lower or product.name.casefold(),
        "calories": float(product.calories),
        "protein": float(product.protein),
        "fat": float(product.fat),
        "carbs": float(product.carbs),
        "is_custom": product.is_custom,
        "owner_id": owner_id,
        "created_at": product.created_at,
    }

    if product.id is not None:
        object_id = parse_object_id(product.id)
        if object_id is None:
            raise ValueError(
                "product.id must be a valid MongoDB ObjectId"
            )
        document["_id"] = object_id

    return document


def product_from_document(document: dict) -> Product:
    """Преобразовать документ в продукт."""
    owner_id = document.get("owner_id")

    return Product(
        id=str(document["_id"]),
        name=document["name"],
        name_lower=document.get("name_lower", ""),
        calories=document["calories"],
        protein=document["protein"],
        fat=document["fat"],
        carbs=document["carbs"],
        is_custom=document.get("is_custom", False),
        owner_id=str(owner_id) if owner_id is not None else None,
        created_at=document["created_at"],
    )


def food_entry_to_document(entry: FoodEntry) -> dict:
    """Подготовить запись дневника со ссылками ObjectId."""
    user_id = parse_object_id(entry.user_id)
    product_id = parse_object_id(entry.product_id)

    if user_id is None:
        raise ValueError(
            "food_entry.user_id must be a valid MongoDB ObjectId"
        )

    if product_id is None:
        raise ValueError(
            "food_entry.product_id must be a valid MongoDB ObjectId"
        )

    document = {
        "user_id": user_id,
        "product_id": product_id,
        "product_name": entry.product_name,
        "grams": float(entry.grams),
        "calories": float(entry.calories),
        "protein": float(entry.protein),
        "fat": float(entry.fat),
        "carbs": float(entry.carbs),
        "meal": entry.meal,
        "date": entry.date,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }

    if entry.id is not None:
        object_id = parse_object_id(entry.id)
        if object_id is None:
            raise ValueError(
                "food_entry.id must be a valid MongoDB ObjectId"
            )
        document["_id"] = object_id

    return document


def food_entry_from_document(document: dict) -> FoodEntry:
    """Преобразовать документ в FoodEntry."""
    return FoodEntry(
        id=str(document["_id"]),
        user_id=str(document["user_id"]),
        product_id=str(document["product_id"]),
        product_name=document["product_name"],
        grams=document["grams"],
        calories=document["calories"],
        protein=document["protein"],
        fat=document["fat"],
        carbs=document["carbs"],
        meal=document["meal"],
        date=document["date"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )
