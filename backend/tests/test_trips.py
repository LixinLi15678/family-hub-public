"""
Tests for trip and budget endpoints
"""
import pytest
from datetime import date, timedelta
from httpx import AsyncClient


@pytest.fixture
async def auth_headers(client: AsyncClient):
    """Create a user and return auth headers"""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "tripuser",
            "email": "trip@example.com",
            "password": "testpassword123"
        }
    )
    
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "trip@example.com",
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
        json={"name": "Trip Test Family"}
    )
    return response.json()["data"]


@pytest.fixture
async def trip_setup(client: AsyncClient, auth_headers: dict, family_setup):
    """Create a trip for testing"""
    start_date = date.today() + timedelta(days=7)
    response = await client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "name": "测试旅行",
            "destination": "测试目的地",
            "start_date": str(start_date),
            "end_date": str(start_date + timedelta(days=5)),
            "total_budget": 10000
        }
    )
    return response.json()["data"]


# ============== Create Trip Tests ==============

@pytest.mark.asyncio
async def test_create_trip(client: AsyncClient, auth_headers: dict, family_setup):
    """测试创建旅行计划"""
    start_date = date.today() + timedelta(days=7)
    end_date = start_date + timedelta(days=5)
    
    response = await client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "name": "东京五日游",
            "destination": "日本东京",
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_budget": 20000
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "东京五日游"
    assert data["data"]["destination"] == "日本东京"
    assert data["data"]["total_budget"] == 20000


@pytest.mark.asyncio
async def test_create_trip_without_family(client: AsyncClient):
    """测试未加入家庭时创建旅行"""
    # Register a new user without joining family
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "nofamilytrip",
            "email": "nofamilytrip@example.com",
            "password": "testpassword123"
        }
    )
    
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nofamilytrip@example.com",
            "password": "testpassword123"
        }
    )
    token = login_response.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = await client.post(
        "/api/v1/trips",
        headers=headers,
        json={
            "name": "测试旅行",
            "destination": "测试地点",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=3))
        }
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_trip_minimal(client: AsyncClient, auth_headers: dict, family_setup):
    """测试创建最简旅行（只有必填字段）"""
    start_date = date.today() + timedelta(days=14)
    
    response = await client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "name": "简单旅行",
            "destination": "附近",
            "start_date": str(start_date),
            "end_date": str(start_date + timedelta(days=1))
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["name"] == "简单旅行"


# ============== Get Trips Tests ==============

@pytest.mark.asyncio
async def test_get_trips(client: AsyncClient, auth_headers: dict, family_setup):
    """测试获取旅行列表"""
    # Create multiple trips
    for i in range(3):
        start_date = date.today() + timedelta(days=7 + i * 10)
        await client.post(
            "/api/v1/trips",
            headers=auth_headers,
            json={
                "name": f"旅行{i+1}",
                "destination": f"目的地{i+1}",
                "start_date": str(start_date),
                "end_date": str(start_date + timedelta(days=3))
            }
        )
    
    response = await client.get("/api/v1/trips", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 3


@pytest.mark.asyncio
async def test_get_trip_by_id(client: AsyncClient, auth_headers: dict, family_setup):
    """测试获取单个旅行详情"""
    # Create a trip
    start_date = date.today() + timedelta(days=7)
    create_response = await client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "name": "详情测试旅行",
            "destination": "测试目的地",
            "start_date": str(start_date),
            "end_date": str(start_date + timedelta(days=3))
        }
    )
    trip_id = create_response.json()["data"]["id"]
    
    # Get the trip
    response = await client.get(f"/api/v1/trips/{trip_id}", headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "详情测试旅行"


@pytest.mark.asyncio
async def test_get_trip_not_found(client: AsyncClient, auth_headers: dict, family_setup):
    """测试获取不存在的旅行"""
    response = await client.get("/api/v1/trips/99999", headers=auth_headers)
    
    assert response.status_code == 404


# ============== Update Trip Tests ==============

@pytest.mark.asyncio
async def test_update_trip(client: AsyncClient, auth_headers: dict, family_setup):
    """测试更新旅行计划"""
    # Create a trip
    start_date = date.today() + timedelta(days=7)
    create_response = await client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "name": "原始旅行",
            "destination": "原始地点",
            "start_date": str(start_date),
            "end_date": str(start_date + timedelta(days=3))
        }
    )
    trip_id = create_response.json()["data"]["id"]
    
    # Update it
    response = await client.put(
        f"/api/v1/trips/{trip_id}",
        headers=auth_headers,
        json={
            "name": "更新后旅行",
            "destination": "更新后地点"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["name"] == "更新后旅行"
    assert data["data"]["destination"] == "更新后地点"


@pytest.mark.asyncio
async def test_update_trip_budget(client: AsyncClient, auth_headers: dict, family_setup):
    """测试更新旅行预算"""
    # Create a trip
    start_date = date.today() + timedelta(days=7)
    create_response = await client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "name": "预算更新测试",
            "destination": "测试",
            "start_date": str(start_date),
            "end_date": str(start_date + timedelta(days=3)),
            "total_budget": 5000
        }
    )
    trip_id = create_response.json()["data"]["id"]
    
    # Update budget
    response = await client.put(
        f"/api/v1/trips/{trip_id}",
        headers=auth_headers,
        json={"total_budget": 10000}
    )
    
    assert response.status_code == 200
    assert response.json()["data"]["total_budget"] == 10000


@pytest.mark.asyncio
async def test_update_trip_not_found(client: AsyncClient, auth_headers: dict, family_setup):
    """测试更新不存在的旅行"""
    response = await client.put(
        "/api/v1/trips/99999",
        headers=auth_headers,
        json={"name": "不存在"}
    )
    
    assert response.status_code == 404


# ============== Delete Trip Tests ==============

@pytest.mark.asyncio
async def test_delete_trip(client: AsyncClient, auth_headers: dict, family_setup):
    """测试删除旅行计划"""
    # Create a trip
    start_date = date.today() + timedelta(days=7)
    create_response = await client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "name": "待删除旅行",
            "destination": "待删除地点",
            "start_date": str(start_date),
            "end_date": str(start_date + timedelta(days=3))
        }
    )
    trip_id = create_response.json()["data"]["id"]
    
    # Delete it
    response = await client.delete(f"/api/v1/trips/{trip_id}", headers=auth_headers)
    
    assert response.status_code == 200
    
    # Verify it's deleted
    get_response = await client.get(f"/api/v1/trips/{trip_id}", headers=auth_headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_trip_not_found(client: AsyncClient, auth_headers: dict, family_setup):
    """测试删除不存在的旅行"""
    response = await client.delete("/api/v1/trips/99999", headers=auth_headers)
    
    assert response.status_code == 404


# ============== Budget Tests ==============

@pytest.mark.asyncio
async def test_add_budget_category(client: AsyncClient, auth_headers: dict, family_setup):
    """测试添加预算分类"""
    # Create a trip
    start_date = date.today() + timedelta(days=7)
    trip_response = await client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "name": "预算测试旅行",
            "destination": "测试",
            "start_date": str(start_date),
            "end_date": str(start_date + timedelta(days=3))
        }
    )
    trip_id = trip_response.json()["data"]["id"]
    
    # Add budgets
    budgets = [
        {"category": "交通", "budget_amount": 3000},
        {"category": "住宿", "budget_amount": 5000},
        {"category": "餐饮", "budget_amount": 2000},
    ]
    
    for budget in budgets:
        response = await client.post(
            f"/api/v1/trips/{trip_id}/budgets",
            headers=auth_headers,
            json=budget
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["category"] == budget["category"]
        assert data["data"]["budget_amount"] == budget["budget_amount"]


@pytest.mark.asyncio
async def test_add_budget_to_nonexistent_trip(client: AsyncClient, auth_headers: dict, family_setup):
    """测试向不存在的旅行添加预算"""
    response = await client.post(
        "/api/v1/trips/99999/budgets",
        headers=auth_headers,
        json={"category": "测试", "budget_amount": 1000}
    )
    
    assert response.status_code == 404


# ============== Expense Tests ==============

@pytest.mark.asyncio
async def test_add_trip_expense(client: AsyncClient, auth_headers: dict, family_setup):
    """测试添加旅行支出"""
    # Create a trip with budget
    start_date = date.today() + timedelta(days=7)
    trip_response = await client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "name": "支出测试旅行",
            "destination": "测试",
            "start_date": str(start_date),
            "end_date": str(start_date + timedelta(days=3))
        }
    )
    trip_id = trip_response.json()["data"]["id"]
    
    # Add a budget
    budget_response = await client.post(
        f"/api/v1/trips/{trip_id}/budgets",
        headers=auth_headers,
        json={"category": "交通", "budget_amount": 3000}
    )
    budget_id = budget_response.json()["data"]["id"]
    
    # Add expense
    response = await client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        headers=auth_headers,
        json={
            "amount": 500,
            "budget_id": budget_id,
            "description": "机票",
            "expense_date": str(start_date)
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["amount"] == 500
    assert data["data"]["description"] == "机票"


@pytest.mark.asyncio
async def test_add_multiple_expenses(client: AsyncClient, auth_headers: dict, family_setup):
    """测试添加多笔旅行支出"""
    # Create a trip with budget
    start_date = date.today() + timedelta(days=7)
    trip_response = await client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "name": "多支出测试",
            "destination": "测试",
            "start_date": str(start_date),
            "end_date": str(start_date + timedelta(days=3)),
            "total_budget": 5000
        }
    )
    trip_id = trip_response.json()["data"]["id"]
    
    # Add budget
    budget_response = await client.post(
        f"/api/v1/trips/{trip_id}/budgets",
        headers=auth_headers,
        json={"category": "餐饮", "budget_amount": 2000}
    )
    budget_id = budget_response.json()["data"]["id"]
    
    # Add multiple expenses
    expenses = [
        {"amount": 100, "description": "早餐"},
        {"amount": 200, "description": "午餐"},
        {"amount": 300, "description": "晚餐"},
    ]
    
    for expense in expenses:
        response = await client.post(
            f"/api/v1/trips/{trip_id}/expenses",
            headers=auth_headers,
            json={
                "amount": expense["amount"],
                "budget_id": budget_id,
                "description": expense["description"]
            }
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_trip_expense(client: AsyncClient, auth_headers: dict, family_setup):
    """测试编辑旅行支出（金额/分类/付款人）"""
    # Create a second member in the same family
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "tripmember2",
            "email": "tripmember2@example.com",
            "password": "testpassword123"
        }
    )
    login2 = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "tripmember2@example.com",
            "password": "testpassword123"
        }
    )
    headers2 = {"Authorization": f"Bearer {login2.json()['data']['access_token']}"}
    await client.post(
        "/api/v1/families/join",
        headers=headers2,
        json={"invite_code": family_setup["invite_code"]}
    )

    # Create trip + two budgets
    start_date = date.today() + timedelta(days=7)
    trip_response = await client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "name": "编辑支出测试旅行",
            "destination": "测试",
            "start_date": str(start_date),
            "end_date": str(start_date + timedelta(days=3))
        }
    )
    trip_id = trip_response.json()["data"]["id"]

    b1 = await client.post(
        f"/api/v1/trips/{trip_id}/budgets",
        headers=auth_headers,
        json={"category": "交通", "budget_amount": 3000}
    )
    b2 = await client.post(
        f"/api/v1/trips/{trip_id}/budgets",
        headers=auth_headers,
        json={"category": "住宿", "budget_amount": 3000}
    )
    budget_1_id = b1.json()["data"]["id"]
    budget_2_id = b2.json()["data"]["id"]

    create_expense = await client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        headers=auth_headers,
        json={
            "amount": 500,
            "budget_id": budget_1_id,
            "description": "机票",
            "expense_date": str(start_date)
        }
    )
    expense_id = create_expense.json()["data"]["id"]

    members = await client.get("/api/v1/families/members", headers=auth_headers)
    all_members = members.json()["data"]
    payer_2 = next(m["user_id"] for m in all_members if m["user_id"] != all_members[0]["user_id"])

    update_response = await client.put(
        f"/api/v1/trips/{trip_id}/expenses/{expense_id}",
        headers=auth_headers,
        json={
            "amount": 888,
            "budget_id": budget_2_id,
            "user_id": payer_2,
            "description": "酒店升级",
            "expense_date": str(start_date + timedelta(days=1))
        }
    )

    assert update_response.status_code == 200
    updated = update_response.json()["data"]
    assert updated["amount"] == 888
    assert updated["budget_id"] == budget_2_id
    assert updated["user_id"] == payer_2
    assert updated["description"] == "酒店升级"
    assert updated["category"] == "住宿"


@pytest.mark.asyncio
async def test_add_expense_to_nonexistent_trip(client: AsyncClient, auth_headers: dict, family_setup):
    """测试向不存在的旅行添加支出"""
    response = await client.post(
        "/api/v1/trips/99999/expenses",
        headers=auth_headers,
        json={"amount": 100, "description": "测试"}
    )
    
    assert response.status_code == 404


# ============== Stats Tests ==============

@pytest.mark.asyncio
async def test_get_trip_stats(client: AsyncClient, auth_headers: dict, family_setup):
    """测试获取预算统计"""
    # Create a trip with budgets and expenses
    start_date = date.today() + timedelta(days=7)
    trip_response = await client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "name": "统计测试旅行",
            "destination": "测试",
            "start_date": str(start_date),
            "end_date": str(start_date + timedelta(days=3)),
            "total_budget": 10000
        }
    )
    trip_id = trip_response.json()["data"]["id"]
    
    # Add budgets
    budget_response = await client.post(
        f"/api/v1/trips/{trip_id}/budgets",
        headers=auth_headers,
        json={"category": "交通", "budget_amount": 5000}
    )
    budget_id = budget_response.json()["data"]["id"]
    
    # Add expenses
    await client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        headers=auth_headers,
        json={
            "amount": 2000,
            "budget_id": budget_id,
            "description": "机票"
        }
    )
    
    # Get stats
    response = await client.get(f"/api/v1/trips/{trip_id}/stats", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_budget"] == 10000
    assert data["total_spent"] == 2000
    assert data["total_remaining"] == 8000


@pytest.mark.asyncio
async def test_get_trip_stats_with_multiple_categories(client: AsyncClient, auth_headers: dict, family_setup):
    """测试多分类预算统计"""
    # Create a trip
    start_date = date.today() + timedelta(days=7)
    trip_response = await client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "name": "多分类统计测试",
            "destination": "测试",
            "start_date": str(start_date),
            "end_date": str(start_date + timedelta(days=5)),
            "total_budget": 15000
        }
    )
    trip_id = trip_response.json()["data"]["id"]
    
    # Add multiple budgets
    budgets = [
        {"category": "交通", "budget_amount": 5000},
        {"category": "住宿", "budget_amount": 6000},
        {"category": "餐饮", "budget_amount": 4000},
    ]
    
    budget_ids = {}
    for budget in budgets:
        response = await client.post(
            f"/api/v1/trips/{trip_id}/budgets",
            headers=auth_headers,
            json=budget
        )
        budget_ids[budget["category"]] = response.json()["data"]["id"]
    
    # Add expenses to different categories
    expenses = [
        {"budget_id": budget_ids["交通"], "amount": 2500, "description": "机票"},
        {"budget_id": budget_ids["住宿"], "amount": 3000, "description": "酒店"},
        {"budget_id": budget_ids["餐饮"], "amount": 500, "description": "午餐"},
    ]
    
    for expense in expenses:
        await client.post(
            f"/api/v1/trips/{trip_id}/expenses",
            headers=auth_headers,
            json=expense
        )
    
    # Get stats
    response = await client.get(f"/api/v1/trips/{trip_id}/stats", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_budget"] == 15000
    assert data["total_spent"] == 6000
    assert data["total_remaining"] == 9000
    assert len(data["by_category"]) == 3
    
    # Verify category stats
    category_map = {c["category"]: c for c in data["by_category"]}
    assert category_map["交通"]["actual"] == 2500
    assert category_map["交通"]["remaining"] == 2500
    assert category_map["住宿"]["actual"] == 3000
    assert category_map["住宿"]["remaining"] == 3000
    assert category_map["餐饮"]["actual"] == 500
    assert category_map["餐饮"]["remaining"] == 3500


@pytest.mark.asyncio
async def test_get_trip_stats_over_budget(client: AsyncClient, auth_headers: dict, family_setup):
    """测试超预算统计"""
    # Create a trip
    start_date = date.today() + timedelta(days=7)
    trip_response = await client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "name": "超预算测试",
            "destination": "测试",
            "start_date": str(start_date),
            "end_date": str(start_date + timedelta(days=3)),
            "total_budget": 1000
        }
    )
    trip_id = trip_response.json()["data"]["id"]
    
    # Add budget
    budget_response = await client.post(
        f"/api/v1/trips/{trip_id}/budgets",
        headers=auth_headers,
        json={"category": "测试分类", "budget_amount": 1000}
    )
    budget_id = budget_response.json()["data"]["id"]
    
    # Add expense over budget
    await client.post(
        f"/api/v1/trips/{trip_id}/expenses",
        headers=auth_headers,
        json={
            "amount": 1500,
            "budget_id": budget_id,
            "description": "超支"
        }
    )
    
    # Get stats
    response = await client.get(f"/api/v1/trips/{trip_id}/stats", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_spent"] == 1500
    assert data["total_remaining"] == -500  # Negative means over budget
    
    # Check category percentage
    category = data["by_category"][0]
    assert category["percentage_used"] == 150.0


@pytest.mark.asyncio
async def test_get_trip_stats_not_found(client: AsyncClient, auth_headers: dict, family_setup):
    """测试获取不存在旅行的统计"""
    response = await client.get("/api/v1/trips/99999/stats", headers=auth_headers)
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_trip_stats_empty(client: AsyncClient, auth_headers: dict, family_setup):
    """测试获取无支出旅行的统计"""
    # Create a trip with budget but no expenses
    start_date = date.today() + timedelta(days=7)
    trip_response = await client.post(
        "/api/v1/trips",
        headers=auth_headers,
        json={
            "name": "空统计测试",
            "destination": "测试",
            "start_date": str(start_date),
            "end_date": str(start_date + timedelta(days=3)),
            "total_budget": 5000
        }
    )
    trip_id = trip_response.json()["data"]["id"]
    
    # Add budget
    await client.post(
        f"/api/v1/trips/{trip_id}/budgets",
        headers=auth_headers,
        json={"category": "交通", "budget_amount": 5000}
    )
    
    # Get stats (no expenses)
    response = await client.get(f"/api/v1/trips/{trip_id}/stats", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_spent"] == 0
    assert data["total_remaining"] == 5000
