"""Сценарии ведения дневника питания."""
from backend.domain.errors import NotFoundError, ValidationError
from backend.domain.models import FoodEntry, validate_date
from backend.domain.nutrition import (
    calculate_portion,
    remaining_nutrients,
    sum_nutrients,
)
from backend.domain.streaks import is_success_day

_ENTRY_FIELDS = ("product_id", "grams", "meal", "date")
_ALLOWED_CHANGES = ("grams", "meal")


class DiaryService:
    """Создание, сводка, изменение и удаление записей дневника."""

    def __init__(self, entries, products, profile_service):
        self._entries = entries
        self._products = products
        self._profiles = profile_service

    def create_entry(self, data, user_id):
        """Рассчитать порцию и сохранить запись со снимком продукта."""
        _require_fields(data, _ENTRY_FIELDS)
        product = self._products.get_by_id(data["product_id"], user_id)
        if product is None:
            raise NotFoundError("Продукт не найден")
        portion = calculate_portion(_nutrients(product), data["grams"])
        entry = FoodEntry(
            user_id=user_id,
            product_id=product.id,
            product_name=product.name,
            grams=data["grams"],
            meal=data["meal"],
            date=data["date"],
            **portion,
        )
        return self._entries.create(entry)

    def get_day(self, date, user_id):
        """Собрать сводку дня: записи, итоги, норму, остаток, успех."""
        validate_date(date)
        entries = self._entries.get_by_user_and_date(user_id, date)
        totals = sum_nutrients(entries)
        _, norm = self._profiles.get_profile(user_id)
        return {
            "date": date,
            "entries": entries,
            "totals": totals,
            "norm": norm,
            "remaining": remaining_nutrients(norm, totals),
            "is_success": is_success_day(
                totals["kcal"], norm["kcal"], len(entries),
            ),
        }

    def update_entry(self, entry_id, data, user_id):
        """Обновить граммы или приём пищи, пересчитав КБЖУ."""
        entry = self._entries.get_by_id(entry_id, user_id)
        if entry is None:
            raise NotFoundError("Запись не найдена")
        _validate_changes(data)

        grams = data.get("grams", entry.grams)
        meal = data.get("meal", entry.meal)
        nutrients = _entry_nutrients(entry)
        if "grams" in data:
            product = self._products.get_by_id(entry.product_id, user_id)
            if product is None:
                raise NotFoundError("Исходный продукт недоступен")
            nutrients = calculate_portion(_nutrients(product), grams)

        updated = FoodEntry(
            id=entry.id,
            user_id=entry.user_id,
            product_id=entry.product_id,
            product_name=entry.product_name,
            grams=grams,
            meal=meal,
            date=entry.date,
            kcal=nutrients["kcal"],
            protein=nutrients["protein"],
            fat=nutrients["fat"],
            carbs=nutrients["carbs"],
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
        saved = self._entries.update(updated, user_id)
        if saved is None:
            raise NotFoundError("Запись не найдена")
        return saved

    def delete_entry(self, entry_id, user_id):
        """Удалить свою запись; чужая или отсутствующая — 404."""
        if not self._entries.delete(entry_id, user_id):
            raise NotFoundError("Запись не найдена")


def _require_fields(data, names):
    """Проверить наличие обязательных полей записи."""
    if not isinstance(data, dict):
        raise ValidationError("Ожидается JSON-объект")
    for name in names:
        if name not in data or data[name] is None:
            raise ValidationError(f"Обязательное поле: {name}", name)


def _validate_changes(changes):
    """Разрешить только граммы и приём пищи, минимум одно поле."""
    if not isinstance(changes, dict) or not changes:
        raise ValidationError("Передайте хотя бы одно поле")
    unknown = sorted(set(changes) - set(_ALLOWED_CHANGES))
    if unknown:
        raise ValidationError(
            "Нельзя изменить поле: " + ", ".join(unknown),
            unknown[0],
        )


def _nutrients(product):
    """Собрать КБЖУ продукта на 100 г для расчёта порции."""
    return {
        "kcal": product.kcal,
        "protein": product.protein,
        "fat": product.fat,
        "carbs": product.carbs,
    }


def _entry_nutrients(entry):
    """Вернуть сохранённые в записи КБЖУ без пересчёта."""
    return {
        "kcal": entry.kcal,
        "protein": entry.protein,
        "fat": entry.fat,
        "carbs": entry.carbs,
    }
