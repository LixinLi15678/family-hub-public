"""
Default seed data for the application.
Used to populate initial data when setting up a new family or database.
"""
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.currency import Currency, ExchangeRate
from app.models.expense import ExpenseCategory
from app.models.shopping import Store


# ============== Default Currencies ==============

DEFAULT_CURRENCIES = [
    {"code": "USD", "name": "美元", "symbol": "$"},
    {"code": "CNY", "name": "人民币", "symbol": "¥"},
    {"code": "HKD", "name": "港币", "symbol": "HK$"},
    {"code": "CAD", "name": "加元", "symbol": "C$"},
    {"code": "JPY", "name": "日元", "symbol": "¥"},
]

# Default exchange rates (relative to USD)
DEFAULT_EXCHANGE_RATES = {
    "CNY": 7.20,
    "HKD": 7.80,
    "CAD": 1.35,
    "JPY": 149.00,
}


# ============== Default Expense Categories ==============

DEFAULT_EXPENSE_CATEGORIES = [
    # 固定开销 - Fixed expenses
    {"name": "房租", "type": "fixed", "icon": "🏠", "sort_order": 1},
    {"name": "水电煤", "type": "fixed", "icon": "💡", "sort_order": 2},
    {"name": "网络/电话", "type": "fixed", "icon": "📱", "sort_order": 3},
    {"name": "保险", "type": "fixed", "icon": "🛡️", "sort_order": 4},
    {"name": "养车", "type": "fixed", "icon": "🚗", "sort_order": 5},
    {"name": "伙食", "type": "fixed", "icon": "🍚", "sort_order": 6},
    
    # 补充开销 - Supplementary expenses
    {"name": "外食", "type": "supplementary", "icon": "🍽️", "sort_order": 10},
    {"name": "交通", "type": "supplementary", "icon": "🚌", "sort_order": 11},
    {"name": "日用品", "type": "fixed", "icon": "🧻", "sort_order": 7},
    {"name": "医疗", "type": "supplementary", "icon": "💊", "sort_order": 13},
    {"name": "教育", "type": "supplementary", "icon": "📚", "sort_order": 14},
    {"name": "宠物", "type": "fixed", "icon": "🐱", "sort_order": 15},
    {"name": "美容美发", "type": "supplementary", "icon": "💇‍♀️", "sort_order": 16},
    {"name": "服装", "type": "supplementary", "icon": "👕", "sort_order": 17},
    {"name": "奶茶小吃", "type": "supplementary", "icon": "🧋", "sort_order": 18},
    
    # 非必要开销 - Optional expenses
    {"name": "娱乐", "type": "optional", "icon": "🎮", "sort_order": 20},
    {"name": "购物", "type": "optional", "icon": "🛍️", "sort_order": 21},
    {"name": "旅游", "type": "optional", "icon": "✈️", "sort_order": 22},
    {"name": "社交", "type": "optional", "icon": "👥", "sort_order": 23},
    {"name": "订阅服务", "type": "supplementary", "icon": "📺", "sort_order": 24},
    {"name": "额外服装", "type": "optional", "icon": "🧥", "sort_order": 25},
    {"name": "互联网消费", "type": "optional", "icon": "💻", "sort_order": 26},

    # 大额开销 - Big expense pool categories
    {"name": "大额开销", "type": "optional", "icon": "💰", "sort_order": 30, "is_big_expense": True},
    {"name": "大额-家电/数码", "type": "optional", "icon": "🖥️", "sort_order": 31, "is_big_expense": True},
    {"name": "大额-旅游/度假", "type": "optional", "icon": "🏖️", "sort_order": 32, "is_big_expense": True},
    {"name": "大额-娱乐", "type": "optional", "icon": "🎓", "sort_order": 33, "is_big_expense": True},

    {"name": "其他", "type": "optional", "icon": "📦", "sort_order": 99},
]


# ============== Default Stores ==============

DEFAULT_STORES = [
    {"name": "Costco", "icon": "🛒", "sort_order": 1},
    {"name": "Weee!", "icon": "🥬", "sort_order": 2},
    {"name": "Sprout", "icon": "🌱", "sort_order": 3},
    {"name": "Whole Foods", "icon": "🍎", "sort_order": 4},
    {"name": "Trader Joe's", "icon": "🌻", "sort_order": 5},
    {"name": "Target", "icon": "🎯", "sort_order": 6},
    {"name": "Amazon", "icon": "📦", "sort_order": 7},
    {"name": "其他", "icon": "🏪", "sort_order": 99},
]


# ============== Default Chore Templates ==============

DEFAULT_CHORE_TEMPLATES = [
    # Daily chores
    {"name": "洗碗", "points_reward": 5, "recurrence": "daily", "description": "清洗餐具"},
    {"name": "倒垃圾", "points_reward": 3, "recurrence": "daily", "description": "倒垃圾并换袋"},
    {"name": "收拾餐桌", "points_reward": 2, "recurrence": "daily", "description": "饭后清理餐桌"},
    
    # Weekly chores
    {"name": "吸尘", "points_reward": 10, "recurrence": "weekly", "description": "全屋吸尘"},
    {"name": "拖地", "points_reward": 10, "recurrence": "weekly", "description": "全屋拖地"},
    {"name": "洗衣服", "points_reward": 8, "recurrence": "weekly", "description": "洗衣+晾晒"},
    {"name": "叠衣服", "points_reward": 5, "recurrence": "weekly", "description": "叠好衣服放回衣柜"},
    {"name": "清洁浴室", "points_reward": 15, "recurrence": "weekly", "description": "清洁马桶、洗手台、淋浴间"},
    {"name": "采购食材", "points_reward": 10, "recurrence": "weekly", "description": "超市采购"},
    
    # Monthly chores
    {"name": "换床单", "points_reward": 10, "recurrence": "monthly", "description": "更换所有床单被套"},
    {"name": "清洁冰箱", "points_reward": 15, "recurrence": "monthly", "description": "清理过期食物，擦拭冰箱"},
    {"name": "整理衣柜", "points_reward": 20, "recurrence": "monthly", "description": "整理换季衣物"},
]


# ============== Seed Functions ==============

async def seed_currencies(db: AsyncSession) -> None:
    """Seed default currencies and exchange rates"""
    # Check if currencies already exist
    result = await db.execute(select(Currency))
    if result.scalars().first():
        return  # Already seeded
    
    currencies = {}
    for currency_data in DEFAULT_CURRENCIES:
        currency = Currency(**currency_data)
        db.add(currency)
        currencies[currency_data["code"]] = currency
    
    await db.flush()
    
    # Refresh to get IDs
    for code, currency in currencies.items():
        await db.refresh(currency)
    
    # Add exchange rates (USD as base)
    usd = currencies["USD"]
    for code, rate in DEFAULT_EXCHANGE_RATES.items():
        if code in currencies:
            exchange_rate = ExchangeRate(
                from_currency_id=usd.id,
                to_currency_id=currencies[code].id,
                rate=rate
            )
            db.add(exchange_rate)
    
    await db.commit()
    print(f"✅ Seeded {len(DEFAULT_CURRENCIES)} currencies and {len(DEFAULT_EXCHANGE_RATES)} exchange rates")


async def seed_expense_categories(db: AsyncSession, family_id: int) -> None:
    """Seed default expense categories for a family"""
    result = await db.execute(
        select(ExpenseCategory).where(ExpenseCategory.family_id == family_id)
    )
    existing = result.scalars().all()
    default_map = {c["name"]: c for c in DEFAULT_EXPENSE_CATEGORIES}
    has_updates = False

    # Handle renamed defaults to avoid duplicates
    rename_map = {
        "房租/房贷": "房租",
        "车贷/养车": "养车",
        "餐饮": "外食",
        "大额-教育/培训": "大额-娱乐",
    }

    # Align existing categories (e.g., if defaults changed)
    for category in existing:
        target_name = rename_map.get(category.name, category.name)
        desired = default_map.get(target_name)
        if not desired:
            continue

        if category.name != desired["name"]:
            category.name = desired["name"]
            has_updates = True
        if category.type != desired["type"]:
            category.type = desired["type"]
            has_updates = True
        if category.sort_order != desired.get("sort_order", category.sort_order):
            category.sort_order = desired.get("sort_order", category.sort_order)
            has_updates = True
        if category.icon != desired.get("icon", category.icon):
            category.icon = desired.get("icon", category.icon)
            has_updates = True
        if category.is_big_expense != desired.get("is_big_expense", False):
            category.is_big_expense = desired.get("is_big_expense", False)
            has_updates = True

    existing_names = {c.name for c in existing}

    to_insert = [
        category_data
        for category_data in DEFAULT_EXPENSE_CATEGORIES
        if category_data["name"] not in existing_names
    ]

    if not to_insert and not has_updates:
        return

    for category_data in to_insert:
        category = ExpenseCategory(
            family_id=family_id,
            **category_data
        )
        db.add(category)
    
    await db.commit()
    print(f"✅ Seeded {len(to_insert)} new expense categories for family {family_id}")
    if has_updates:
        print(f"🔄 Updated {family_id} existing categories to match defaults")


async def seed_stores(db: AsyncSession, family_id: int) -> None:
    """Seed default stores for a family"""
    # Check if family already has stores
    result = await db.execute(
        select(Store).where(Store.family_id == family_id)
    )
    if result.scalars().first():
        return  # Already seeded
    
    for store_data in DEFAULT_STORES:
        store = Store(
            family_id=family_id,
            **store_data
        )
        db.add(store)
    
    await db.commit()
    print(f"✅ Seeded {len(DEFAULT_STORES)} stores for family {family_id}")


async def seed_family_defaults(db: AsyncSession, family_id: int) -> None:
    """
    Seed all default data for a new family.
    Called when a new family is created.
    """
    await seed_expense_categories(db, family_id)
    await seed_stores(db, family_id)


async def seed_all(db: AsyncSession) -> None:
    """
    Seed all global default data.
    Called during application startup or database initialization.
    """
    await seed_currencies(db)


def get_chore_templates() -> List[Dict[str, Any]]:
    """
    Get list of chore templates that can be used as suggestions
    when creating new chores.
    """
    return DEFAULT_CHORE_TEMPLATES.copy()


def get_category_suggestions() -> List[Dict[str, Any]]:
    """
    Get list of category suggestions for the frontend.
    """
    return [
        {"name": cat["name"], "icon": cat["icon"], "type": cat["type"]}
        for cat in DEFAULT_EXPENSE_CATEGORIES
    ]


def get_store_suggestions() -> List[Dict[str, Any]]:
    """
    Get list of store suggestions for the frontend.
    """
    return [
        {"name": store["name"], "icon": store["icon"]}
        for store in DEFAULT_STORES
    ]
