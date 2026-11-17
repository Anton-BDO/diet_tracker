"""Проверка качества данных стартового справочника.

Значения справочные (USDA и таблицы состава РФ), на 100 г. Состав
готового блюда зависит от рецепта; допускается расхождение ккал с
расчётом 4/9/4 на округление и клетчатку.
"""
import json
import math


from scripts import seed_products
from scripts.build_seed import DISH_NAMES

MIN_TOTAL = 250
MIN_DISHES = 60
KCAL_TOLERANCE = 50.0
ZERO_KCAL_ALLOWED = {"вода без газа", "чай чёрный без сахара",
                     "кофе черный без сахара"}

REQUIRED_NAMES = [
    "Банан", "Куриная грудка сырая", "Творог 5%", "Гречка отварная",
    "Овсяная каша на молоке", "Борщ", "Плов с курицей", "Сырники жареные",
    "Пельмени отварные", "Оливье с курицей", "Винегрет",
    "Картофельное пюре на молоке", "Молоко 2,5%", "Яйцо куриное сырое",
    "Масло оливковое", "Орех грецкий", "Мёд", "Горбуша сырая",
]


def _items():
    raw = seed_products.PRODUCTS_FILE.read_text(encoding="utf-8")
    return json.loads(raw)


def test_catalog_size_and_dish_count():
    items = _items()
    assert len(items) >= MIN_TOTAL
    dishes = [item for item in items if item["name"] in DISH_NAMES]
    assert len(dishes) >= MIN_DISHES
    # Базовые продукты не считаются блюдами.
    for name in ("Рис отварной", "Тунец консервированный в собственном соку",
                 "Кальмар варёный", "Яйцо варёное"):
        assert name not in DISH_NAMES, f"{name}: не блюдо"


def test_no_duplicate_normalized_names():
    items = _items()
    names = [" ".join(item["name"].casefold().split()) for item in items]
    assert len(names) == len(set(names))


def test_required_names_present():
    names = {item["name"] for item in _items()}
    missing = [name for name in REQUIRED_NAMES if name not in names]
    assert not missing, f"нет обязательных позиций: {missing}"


def test_nutrients_within_allowed_ranges():
    for item in _items():
        label = item["name"]
        assert item["name"].strip(), "пустое название"
        kcal = item["kcal"]
        protein, fat, carbs = (item["protein"], item["fat"], item["carbs"])
        for value in (kcal, protein, fat, carbs):
            assert isinstance(value, (int, float)) and not isinstance(
                value, bool), f"{label}: не число"
            assert math.isfinite(value), f"{label}: не конечное значение"
        assert 0 <= kcal <= 1000, f"{label}: ккал вне диапазона"
        for value in (protein, fat, carbs):
            assert 0 <= value <= 100, f"{label}: БЖУ вне диапазона"


def test_kcal_match_4_9_4_calculation():
    for item in _items():
        expected = item["protein"] * 4 + item["fat"] * 9 + item["carbs"] * 4
        diff = abs(item["kcal"] - expected)
        assert diff <= KCAL_TOLERANCE, (
            f"{item['name']}: ккал {item['kcal']} расходятся с расчётом "
            f"{expected:.1f} больше чем на {KCAL_TOLERANCE}"
        )


def test_zero_kcal_only_for_drinks():
    for item in _items():
        if item["kcal"] == 0:
            assert item["name"].casefold() in ZERO_KCAL_ALLOWED, (
                f"{item['name']}: нулевая калорийность без оснований"
            )


def test_dishes_are_not_all_zero_nutrients():
    for item in _items():
        if item["kcal"] > 0:
            total = item["protein"] + item["fat"] + item["carbs"]
            assert total > 0, f"{item['name']}: все нутриенты нулевые"
