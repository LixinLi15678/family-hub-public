"""
Tests for expense endpoints
"""
import pytest
from datetime import date
from httpx import AsyncClient


@pytest.fixture
async def auth_headers(client: AsyncClient):
    """Create a user and return auth headers"""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "expenseuser",
            "email": "expense@example.com",
            "password": "testpassword123"
        }
    )
    
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "expense@example.com",
            "password": "testpassword123"
        }
    )
    data = response.json()
    token = data["data"]["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def family_setup(client: AsyncClient, auth_headers: dict):
    """Create a family for testing"""
    response = await client.post(
        "/api/v1/families",
        headers=auth_headers,
        json={"name": "Expense Test Family"}
    )
    return response.json()["data"]


@pytest.fixture
async def category_setup(client: AsyncClient, auth_headers: dict, family_setup):
    """Create expense categories for testing"""
    # Create a category
    response = await client.post(
        "/api/v1/expenses/categories",
        headers=auth_headers,
        json={
            "name": "食品",
            "type": "fixed",
            "icon": "🍕"
        }
    )
    return response.json()["data"]


@pytest.fixture
async def currency_id():
    """Return default currency ID (USD = 1)"""
    return 1


# ============== Categories Tests ==============

@pytest.mark.asyncio
async def test_create_category(client: AsyncClient, auth_headers: dict, family_setup):
    """Test creating an expense category"""
    response = await client.post(
        "/api/v1/expenses/categories",
        headers=auth_headers,
        json={
            "name": "交通",
            "type": "supplementary",
            "icon": "🚗"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "交通"
    assert data["data"]["type"] == "supplementary"


@pytest.mark.asyncio
async def test_create_subcategory(client: AsyncClient, auth_headers: dict, family_setup):
    """Test creating a subcategory"""
    # Create parent category
    parent_response = await client.post(
        "/api/v1/expenses/categories",
        headers=auth_headers,
        json={
            "name": "外食",
            "type": "fixed"
        }
    )
    parent_id = parent_response.json()["data"]["id"]
    
    # Create subcategory
    response = await client.post(
        "/api/v1/expenses/categories",
        headers=auth_headers,
        json={
            "name": "外卖",
            "type": "fixed",
            "parent_id": parent_id
        }
    )
    
    assert response.status_code == 200
    assert response.json()["data"]["parent_id"] == parent_id


@pytest.mark.asyncio
async def test_get_categories(client: AsyncClient, auth_headers: dict, family_setup):
    """Test getting all categories"""
    # Create categories
    categories = [
        {"name": "食品", "type": "fixed"},
        {"name": "住房", "type": "fixed"},
        {"name": "娱乐", "type": "optional"}
    ]
    for cat in categories:
        await client.post(
            "/api/v1/expenses/categories",
            headers=auth_headers,
            json=cat
        )
    
    response = await client.get(
        "/api/v1/expenses/categories",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) >= 3


# ============== Expenses Tests ==============

@pytest.mark.asyncio
async def test_create_expense(client: AsyncClient, auth_headers: dict, family_setup, category_setup, currency_id):
    """Test creating an expense"""
    response = await client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "category_id": category_setup["id"],
            "amount": 50.00,
            "currency_id": currency_id,
            "description": "晚餐",
            "expense_date": str(date.today())
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert float(data["data"]["amount"]) == 50.00
    assert data["data"]["description"] == "晚餐"


@pytest.mark.asyncio
async def test_create_expense_with_splits(client: AsyncClient, auth_headers: dict, family_setup, category_setup, currency_id):
    """Test creating an expense with splits"""
    # Get user ID from family members
    members_response = await client.get(
        "/api/v1/families/members",
        headers=auth_headers
    )
    user_id = members_response.json()["data"][0]["id"]
    
    response = await client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "category_id": category_setup["id"],
            "amount": 100.00,
            "currency_id": currency_id,
            "description": "团购",
            "expense_date": str(date.today()),
            "splits": [
                {"user_id": user_id, "share_amount": 100.00, "share_percentage": 100}
            ]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["splits"] is not None
    assert len(data["data"]["splits"]) == 1


@pytest.mark.asyncio
async def test_create_split_only_expense(client: AsyncClient, auth_headers: dict, family_setup, category_setup, currency_id):
    """Split-only expense should not 500 (no async lazy-load MissingGreenlet)."""
    members_response = await client.get(
        "/api/v1/families/members",
        headers=auth_headers
    )
    user_id = members_response.json()["data"][0]["id"]

    response = await client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "category_id": category_setup["id"],
            "amount": 100.00,
            "currency_id": currency_id,
            "description": "split-only settlement",
            "expense_date": str(date.today()),
            "split_only": True,
            "splits": [
                {"user_id": user_id, "share_amount": 100.00, "share_percentage": 100}
            ]
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["split_only"] is True


@pytest.mark.asyncio
async def test_get_expenses(client: AsyncClient, auth_headers: dict, family_setup, category_setup, currency_id):
    """Test getting expenses with pagination"""
    # Create multiple expenses
    for i in range(5):
        await client.post(
            "/api/v1/expenses",
            headers=auth_headers,
            json={
                "category_id": category_setup["id"],
                "amount": 10.00 * (i + 1),
                "currency_id": currency_id,
                "expense_date": str(date.today())
            }
        )
    
    response = await client.get(
        "/api/v1/expenses",
        headers=auth_headers,
        params={"page": 1, "page_size": 3}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["items"]) == 3
    assert data["data"]["total"] == 5


@pytest.mark.asyncio
async def test_get_expenses_filter_by_category(client: AsyncClient, auth_headers: dict, family_setup, category_setup, currency_id):
    """Test filtering expenses by category"""
    # Create another category
    other_cat_response = await client.post(
        "/api/v1/expenses/categories",
        headers=auth_headers,
        json={"name": "其他", "type": "optional"}
    )
    other_cat_id = other_cat_response.json()["data"]["id"]
    
    # Create expenses in different categories
    await client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "category_id": category_setup["id"],
            "amount": 20.00,
            "currency_id": currency_id,
            "expense_date": str(date.today())
        }
    )
    await client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "category_id": other_cat_id,
            "amount": 30.00,
            "currency_id": currency_id,
            "expense_date": str(date.today())
        }
    )
    
    # Filter by category
    response = await client.get(
        "/api/v1/expenses",
        headers=auth_headers,
        params={"category_id": category_setup["id"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    for item in data["data"]["items"]:
        assert item["category_id"] == category_setup["id"]


@pytest.mark.asyncio
async def test_get_expense_by_id(client: AsyncClient, auth_headers: dict, family_setup, category_setup, currency_id):
    """Test getting a specific expense"""
    # Create expense
    create_response = await client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "category_id": category_setup["id"],
            "amount": 75.00,
            "currency_id": currency_id,
            "expense_date": str(date.today())
        }
    )
    expense_id = create_response.json()["data"]["id"]
    
    # Get expense
    response = await client.get(
        f"/api/v1/expenses/{expense_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert float(response.json()["data"]["amount"]) == 75.00


@pytest.mark.asyncio
async def test_update_expense(client: AsyncClient, auth_headers: dict, family_setup, category_setup, currency_id):
    """Test updating an expense"""
    # Create expense
    create_response = await client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "category_id": category_setup["id"],
            "amount": 50.00,
            "currency_id": currency_id,
            "expense_date": str(date.today())
        }
    )
    expense_id = create_response.json()["data"]["id"]
    version = create_response.json()["data"]["version"]
    
    # Update expense
    response = await client.put(
        f"/api/v1/expenses/{expense_id}",
        headers=auth_headers,
        json={
            "amount": 75.00,
            "description": "Updated description",
            "version": version
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert float(data["data"]["amount"]) == 75.00
    assert data["data"]["description"] == "Updated description"


@pytest.mark.asyncio
async def test_delete_expense(client: AsyncClient, auth_headers: dict, family_setup, category_setup, currency_id):
    """Test deleting an expense"""
    # Create expense
    create_response = await client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "category_id": category_setup["id"],
            "amount": 25.00,
            "currency_id": currency_id,
            "expense_date": str(date.today())
        }
    )
    expense_id = create_response.json()["data"]["id"]
    
    # Delete expense
    response = await client.delete(
        f"/api/v1/expenses/{expense_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    
    # Verify deletion
    get_response = await client.get(
        f"/api/v1/expenses/{expense_id}",
        headers=auth_headers
    )
    assert get_response.status_code == 404


# ============== Splits Tests ==============

@pytest.mark.asyncio
async def test_set_expense_splits(client: AsyncClient, auth_headers: dict, family_setup, category_setup, currency_id):
    """Test setting expense splits"""
    # Create expense
    create_response = await client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "category_id": category_setup["id"],
            "amount": 100.00,
            "currency_id": currency_id,
            "expense_date": str(date.today())
        }
    )
    expense_id = create_response.json()["data"]["id"]
    
    # Get user ID
    members_response = await client.get(
        "/api/v1/families/members",
        headers=auth_headers
    )
    user_id = members_response.json()["data"][0]["id"]
    
    # Set splits
    response = await client.post(
        f"/api/v1/expenses/{expense_id}/splits",
        headers=auth_headers,
        json=[
            {"user_id": user_id, "share_amount": 50.00, "share_percentage": 50}
        ]
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert float(data["data"][0]["share_amount"]) == 50.00


@pytest.mark.asyncio
async def test_mark_split_paid(client: AsyncClient, auth_headers: dict, family_setup, category_setup, currency_id):
    """Test marking a split as paid"""
    # Create expense with split
    members_response = await client.get(
        "/api/v1/families/members",
        headers=auth_headers
    )
    user_id = members_response.json()["data"][0]["id"]
    
    create_response = await client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "category_id": category_setup["id"],
            "amount": 100.00,
            "currency_id": currency_id,
            "expense_date": str(date.today()),
            "splits": [
                {"user_id": user_id, "share_amount": 100.00}
            ]
        }
    )
    split_id = create_response.json()["data"]["splits"][0]["id"]
    
    # Mark as paid
    response = await client.patch(
        f"/api/v1/expenses/splits/{split_id}/pay",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["is_paid"] is True
    assert data["data"]["paid_at"] is not None


# ============== Statistics Tests ==============

@pytest.mark.asyncio
async def test_get_monthly_stats(client: AsyncClient, auth_headers: dict, family_setup, category_setup, currency_id):
    """Test getting monthly statistics"""
    today = date.today()
    
    # Create some expenses
    for amount in [100, 200, 150]:
        await client.post(
            "/api/v1/expenses",
            headers=auth_headers,
            json={
                "category_id": category_setup["id"],
                "amount": amount,
                "currency_id": currency_id,
                "expense_date": str(today)
            }
        )
    
    # Get monthly stats
    response = await client.get(
        "/api/v1/expenses/stats/monthly",
        headers=auth_headers,
        params={"year": today.year, "month": today.month}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["year"] == today.year
    assert data["data"]["month"] == today.month
    assert data["data"]["total_expense"] == 450.00


@pytest.mark.asyncio
async def test_get_category_stats(client: AsyncClient, auth_headers: dict, family_setup, category_setup, currency_id):
    """Test getting category statistics"""
    # Create another category
    other_cat_response = await client.post(
        "/api/v1/expenses/categories",
        headers=auth_headers,
        json={"name": "购物", "type": "optional"}
    )
    other_cat_id = other_cat_response.json()["data"]["id"]
    
    # Create expenses in different categories
    await client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "category_id": category_setup["id"],
            "amount": 100.00,
            "currency_id": currency_id,
            "expense_date": str(date.today())
        }
    )
    await client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "category_id": other_cat_id,
            "amount": 200.00,
            "currency_id": currency_id,
            "expense_date": str(date.today())
        }
    )
    
    # Get category stats
    response = await client.get(
        "/api/v1/expenses/stats/category",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) >= 2
    
    # Verify percentages
    total = sum(cat["total_amount"] for cat in data["data"])
    assert total == 300.00


@pytest.mark.asyncio
async def test_get_monthly_trend(client: AsyncClient, auth_headers: dict, family_setup, category_setup, currency_id):
    """Test getting monthly trend data"""
    today = date.today()
    
    # Create some expenses this month
    for amount in [100, 200, 300]:
        await client.post(
            "/api/v1/expenses",
            headers=auth_headers,
            json={
                "category_id": category_setup["id"],
                "amount": amount,
                "currency_id": currency_id,
                "expense_date": str(today)
            }
        )
    
    # Get monthly trend
    response = await client.get(
        "/api/v1/expenses/stats/monthly-trend",
        headers=auth_headers,
        params={"months": 6}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 6
    
    # Verify data structure
    for item in data["data"]:
        assert "year" in item
        assert "month" in item
        assert "label" in item
        assert "total" in item
    
    # Current month should have our expenses
    current_month_data = next(
        (d for d in data["data"] if d["year"] == today.year and d["month"] == today.month),
        None
    )
    assert current_month_data is not None
    assert current_month_data["total"] == 600.00


@pytest.mark.asyncio
async def test_get_monthly_trend_custom_months(client: AsyncClient, auth_headers: dict, family_setup):
    """Test getting monthly trend with custom month count"""
    # Get trend for 3 months
    response = await client.get(
        "/api/v1/expenses/stats/monthly-trend",
        headers=auth_headers,
        params={"months": 3}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 3


@pytest.mark.asyncio
async def test_get_monthly_trend_no_family(client: AsyncClient):
    """Test getting monthly trend without family"""
    # Register user without family
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "nofamily",
            "email": "nofamily@example.com",
            "password": "testpassword123"
        }
    )
    
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nofamily@example.com",
            "password": "testpassword123"
        }
    )
    token = login_response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to get trend
    response = await client.get(
        "/api/v1/expenses/stats/monthly-trend",
        headers=headers
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_split_only_expense_shown_in_ledger_but_excluded_from_stats(
    client: AsyncClient,
    auth_headers: dict,
    family_setup,
    category_setup,
    currency_id
):
    """Split-only source expenses should appear in ledger, but not affect monthly/category/trend stats."""
    # Create a second user and join the same family
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "member2",
            "email": "member2@example.com",
            "password": "testpassword123"
        }
    )
    login2 = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "member2@example.com",
            "password": "testpassword123"
        }
    )
    token2 = login2.json()["data"]["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    await client.post(
        "/api/v1/families/join",
        headers=headers2,
        json={"invite_code": family_setup["invite_code"]}
    )

    members = await client.get("/api/v1/families/members", headers=auth_headers)
    member_list = members.json()["data"]
    payer_id = member_list[0]["id"]
    debtor_id = next(m["id"] for m in member_list if m["id"] != payer_id)

    today = date.today()

    # Normal expense: should appear in ledger
    await client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "category_id": category_setup["id"],
            "amount": 100.00,
            "currency_id": currency_id,
            "expense_date": str(today)
        }
    )

    # Split-only expense: shown in ledger history and used by settlements
    await client.post(
        "/api/v1/expenses",
        headers=auth_headers,
        json={
            "category_id": category_setup["id"],
            "amount": 50.00,
            "currency_id": currency_id,
            "expense_date": str(today),
            "user_id": payer_id,
            "split_only": True,
            "splits": [
                {"user_id": debtor_id, "share_amount": 50.00}
            ]
        }
    )

    # Ledger list includes split-only source expense
    list_resp = await client.get("/api/v1/expenses", headers=auth_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["data"]["total"] == 2
    assert any(e["split_only"] is True for e in list_resp.json()["data"]["items"])
    assert all(e.get("allocation_source_id") in (None, 0) for e in list_resp.json()["data"]["items"])

    # Monthly stats exclude split-only
    stats_resp = await client.get(
        "/api/v1/expenses/stats/monthly",
        headers=auth_headers,
        params={"year": today.year, "month": today.month}
    )
    assert stats_resp.status_code == 200
    assert stats_resp.json()["data"]["total_expense"] == 100.00

    # Category stats exclude split-only
    cat_resp = await client.get("/api/v1/expenses/stats/category", headers=auth_headers)
    assert cat_resp.status_code == 200
    assert sum(c["total_amount"] for c in cat_resp.json()["data"]) == 100.00

    # Monthly trend excludes split-only
    trend_resp = await client.get(
        "/api/v1/expenses/stats/monthly-trend",
        headers=auth_headers,
        params={"months": 1}
    )
    assert trend_resp.status_code == 200
    assert trend_resp.json()["data"][0]["total"] == 100.00

    # Settlement includes split-only
    settle_resp = await client.get("/api/v1/expenses/stats/splits/settlements", headers=auth_headers)
    assert settle_resp.status_code == 200
    settlements = settle_resp.json()["data"]
    assert any(
        s["from_user_id"] == debtor_id and s["to_user_id"] == payer_id and s["amount"] == 50.00
        for s in settlements
    )
