"""
API routers
"""
from app.routers.auth import router as auth_router
from app.routers.families import router as families_router
from app.routers.shopping import router as shopping_router
from app.routers.expenses import router as expenses_router
from app.routers.incomes import router as incomes_router
from app.routers.currencies import router as currencies_router
from app.routers.chores import router as chores_router
from app.routers.products import router as products_router
from app.routers.trips import router as trips_router
from app.routers.users import router as users_router
from app.routers.export import router as export_router
from app.routers.admin import router as admin_router
from app.routers.todos import router as todos_router

__all__ = [
    "auth_router",
    "families_router",
    "shopping_router",
    "expenses_router",
    "incomes_router",
    "currencies_router",
    "chores_router",
    "products_router",
    "trips_router",
    "users_router",
    "export_router",
    "admin_router",
    "todos_router",
]
