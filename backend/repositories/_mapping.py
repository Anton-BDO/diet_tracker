"""Преобразования BSON и доменных моделей."""

from bson import ObjectId

from backend.domain.models import FoodEntry, Product, Session, User


def parse_object_id(value: str | ObjectId | None) -> ObjectId | None:
    """Преобразовать идентификатор в ObjectId или вернуть None."""
    if isinstance(value, ObjectId):
        return value

    if not isinstance(value, str) or not ObjectId.is_valid(value):
        return None

    return ObjectId(value)


def _required_object_id(value: str | ObjectId, field: str) -> ObjectId:
    """Преобразовать обязательный идентификатор."""
    object_id = parse_object_id(value)

    if object_id is None:
        raise ValueError(
            f"{field} must be a valid MongoDB ObjectId"
        )

    return object_id


def user_to_document(user: User) -> dict:
    """Преобразовать пользователя в документ MongoDB."""
    document = {
        "email": user.email.strip().lower(),
        "password_hash": user.password_hash,
        "name": user.name,
        "sex": user.sex,
        "birth_date": user.birth_date,
        "height_cm": float(user.height_cm),
        "weight_kg": float(user.weight_kg),
        "activity": float(user.activity),
        "goal": user.goal,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }

    if user.id is not None:
        document["_id"] = _required_object_id(user.id, "user.id")

    return document


def user_from_document(document: dict) -> User:
    """Преобразовать документ MongoDB в пользователя."""
    return User(
        id=str(document["_id"]),
        email=document["email"],
        password_hash=document["password_hash"],
        name=document["name"],
        sex=document["sex"],
        birth_date=document["birth_date"],
        height_cm=document["height_cm"],
        weight_kg=document["weight_kg"],
        activity=document["activity"],
        goal=document["goal"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def product_to_document(product: Product) -> dict:
    """Преобразовать продукт в документ MongoDB."""
    owner_id = None

    if product.owner_id is not None:
        owner_id = _required_object_id(
            product.owner_id,
            "product.owner_id",
        )

    document = {
        "name": product.name,
        "name_lower": product.name_lower or product.name.casefold(),
        "kcal": float(product.kcal),
        "protein": float(product.protein),
        "fat": float(product.fat),
        "carbs": float(product.carbs),
        "owner_id": owner_id,
        "created_at": product.created_at,
    }

    if product.id is not None:
        document["_id"] = _required_object_id(
            product.id,
            "product.id",
        )

    return document


def product_from_document(document: dict) -> Product:
    """Преобразовать документ MongoDB в продукт."""
    owner_id = document.get("owner_id")

    return Product(
        id=str(document["_id"]),
        name=document["name"],
        name_lower=document.get("name_lower", ""),
        kcal=document["kcal"],
        protein=document["protein"],
        fat=document["fat"],
        carbs=document["carbs"],
        owner_id=str(owner_id) if owner_id is not None else None,
        created_at=document["created_at"],
    )


def food_entry_to_document(entry: FoodEntry) -> dict:
    """Преобразовать запись дневника в документ MongoDB."""
    document = {
        "user_id": _required_object_id(
            entry.user_id,
            "food_entry.user_id",
        ),
        "product_id": _required_object_id(
            entry.product_id,
            "food_entry.product_id",
        ),
        "product_name": entry.product_name,
        "date": entry.date,
        "meal": entry.meal,
        "grams": float(entry.grams),
        "kcal": float(entry.kcal),
        "protein": float(entry.protein),
        "fat": float(entry.fat),
        "carbs": float(entry.carbs),
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }

    if entry.id is not None:
        document["_id"] = _required_object_id(
            entry.id,
            "food_entry.id",
        )

    return document


def food_entry_from_document(document: dict) -> FoodEntry:
    """Преобразовать документ MongoDB в запись дневника."""
    return FoodEntry(
        id=str(document["_id"]),
        user_id=str(document["user_id"]),
        product_id=str(document["product_id"]),
        product_name=document["product_name"],
        date=document["date"],
        meal=document["meal"],
        grams=document["grams"],
        kcal=document["kcal"],
        protein=document["protein"],
        fat=document["fat"],
        carbs=document["carbs"],
        created_at=document["created_at"],
        updated_at=document["updated_at"],
    )


def session_to_document(session: Session) -> dict:
    """Преобразовать сессию в документ MongoDB."""
    document = {
        "token": session.token,
        "user_id": _required_object_id(session.user_id, "session.user_id"),
        "created_at": session.created_at,
        "expires_at": session.expires_at,
    }

    if session.id is not None:
        document["_id"] = _required_object_id(session.id, "session.id")

    return document


def session_from_document(document: dict) -> Session:
    """Преобразовать документ MongoDB в доменную сессию."""
    return Session(
        id=str(document["_id"]),
        token=document["token"],
        user_id=str(document["user_id"]),
        created_at=document["created_at"],
        expires_at=document["expires_at"],
    )
