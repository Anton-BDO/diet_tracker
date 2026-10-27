"""Репозитории доступа к MongoDB.

BSON преобразуется внутри этого слоя.
"""

from backend.repositories.food_entry_repository import FoodEntryRepository
from backend.repositories.product_repository import ProductRepository
from backend.repositories.session_repository import SessionRepository
from backend.repositories.user_repository import UserRepository

__all__ = [
    "FoodEntryRepository",
    "ProductRepository",
    "SessionRepository",
    "UserRepository",
]
