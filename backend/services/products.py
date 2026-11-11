"""Сценарии поиска и создания продуктов."""
from backend.domain.errors import ValidationError
from backend.domain.models import Product

_PRODUCT_FIELDS = ("name", "kcal", "protein", "fat", "carbs")


class ProductsService:
    """Поиск по общему справочнику и продуктам пользователя."""

    def __init__(self, products):
        self._products = products

    def search(self, query, user_id):
        """Найти доступные продукты по подстроке без учёта регистра."""
        if query is None:
            query = ""
        if not isinstance(query, str):
            raise ValidationError("Параметр q должен быть строкой", "q")
        return self._products.search(query, user_id)

    def create(self, data, user_id):
        """Создать продукт текущего пользователя."""
        if not isinstance(data, dict):
            raise ValidationError("Ожидается JSON-объект")
        for field in _PRODUCT_FIELDS:
            if field not in data or data[field] is None:
                raise ValidationError(f"Обязательное поле: {field}", field)
        return self._products.create(Product(
            name=data["name"],
            kcal=data["kcal"],
            protein=data["protein"],
            fat=data["fat"],
            carbs=data["carbs"],
            owner_id=user_id,
        ))
