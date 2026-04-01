"""
Tests for chore and points endpoints
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
            "username": "choreuser",
            "email": "chore@example.com",
            "password": "testpassword123"
        }
    )
    
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "chore@example.com",
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
        json={"name": "Chore Test Family"}
    )
    return response.json()["data"]


# ============== Create Chore Tests ==============

@pytest.mark.asyncio
async def test_create_chore(client: AsyncClient, auth_headers: dict, family_setup):
    """测试创建家务任务"""
    response = await client.post(
        "/api/v1/chores",
        headers=auth_headers,
        json={
            "name": "打扫客厅",
            "description": "吸尘+拖地",
            "points_reward": 10,
            "recurrence": "weekly"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "打扫客厅"
    assert data["data"]["points_reward"] == 10
    assert data["data"]["recurrence"] == "weekly"
    assert data["data"]["is_active"] is True


@pytest.mark.asyncio
async def test_create_chore_without_family(client: AsyncClient, auth_headers: dict):
    """测试未加入家庭时创建家务"""
    response = await client.post(
        "/api/v1/chores",
        headers=auth_headers,
        json={
            "name": "测试任务",
            "points_reward": 5
        }
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_chore_with_due_date(client: AsyncClient, auth_headers: dict, family_setup):
    """测试创建带截止日期的家务"""
    response = await client.post(
        "/api/v1/chores",
        headers=auth_headers,
        json={
            "name": "一次性任务",
            "points_reward": 20,
            "recurrence": "once",
            "due_date": str(date.today())
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["recurrence"] == "once"
    assert data["data"]["due_date"] is not None


@pytest.mark.asyncio
async def test_create_chore_with_assigned_user(client: AsyncClient, auth_headers: dict, family_setup):
    """测试创建指派给特定成员的家务"""
    # Get current user ID
    user_response = await client.get("/api/v1/users/me", headers=auth_headers)
    user_id = user_response.json()["data"]["id"]
    
    response = await client.post(
        "/api/v1/chores",
        headers=auth_headers,
        json={
            "name": "指派任务",
            "points_reward": 8,
            "assigned_to": user_id
        }
    )
    
    assert response.status_code == 200
    assert response.json()["data"]["assigned_to"] == user_id


# ============== Get Chores Tests ==============

@pytest.mark.asyncio
async def test_get_chores(client: AsyncClient, auth_headers: dict, family_setup):
    """测试获取家务列表"""
    # Create multiple chores
    chores = [
        {"name": "洗碗", "points_reward": 5},
        {"name": "倒垃圾", "points_reward": 3},
        {"name": "洗衣服", "points_reward": 8}
    ]
    for chore in chores:
        await client.post("/api/v1/chores", headers=auth_headers, json=chore)
    
    # Get chores
    response = await client.get("/api/v1/chores", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 3


@pytest.mark.asyncio
async def test_get_chores_filter_by_active(client: AsyncClient, auth_headers: dict, family_setup):
    """测试按活动状态筛选家务"""
    # Create a chore
    create_response = await client.post(
        "/api/v1/chores",
        headers=auth_headers,
        json={"name": "活动任务", "points_reward": 5}
    )
    chore_id = create_response.json()["data"]["id"]
    
    # Deactivate it
    await client.put(
        f"/api/v1/chores/{chore_id}",
        headers=auth_headers,
        json={"is_active": False}
    )
    
    # Get only active chores
    response = await client.get(
        "/api/v1/chores",
        headers=auth_headers,
        params={"is_active": True}
    )
    
    data = response.json()
    for chore in data["data"]:
        assert chore["is_active"] is True


# ============== Update Chore Tests ==============

@pytest.mark.asyncio
async def test_update_chore(client: AsyncClient, auth_headers: dict, family_setup):
    """测试更新家务任务"""
    # Create a chore
    create_response = await client.post(
        "/api/v1/chores",
        headers=auth_headers,
        json={"name": "原始名称", "points_reward": 5}
    )
    chore_id = create_response.json()["data"]["id"]
    
    # Update it
    response = await client.put(
        f"/api/v1/chores/{chore_id}",
        headers=auth_headers,
        json={"name": "更新后名称", "points_reward": 10}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["name"] == "更新后名称"
    assert data["data"]["points_reward"] == 10


@pytest.mark.asyncio
async def test_update_chore_not_found(client: AsyncClient, auth_headers: dict, family_setup):
    """测试更新不存在的家务"""
    response = await client.put(
        "/api/v1/chores/99999",
        headers=auth_headers,
        json={"name": "不存在"}
    )
    
    assert response.status_code == 404


# ============== Delete Chore Tests ==============

@pytest.mark.asyncio
async def test_delete_chore(client: AsyncClient, auth_headers: dict, family_setup):
    """测试删除家务任务"""
    # Create a chore
    create_response = await client.post(
        "/api/v1/chores",
        headers=auth_headers,
        json={"name": "待删除任务", "points_reward": 5}
    )
    chore_id = create_response.json()["data"]["id"]
    
    # Delete it
    response = await client.delete(
        f"/api/v1/chores/{chore_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200


# ============== Complete Chore Tests ==============

@pytest.mark.asyncio
async def test_complete_chore(client: AsyncClient, auth_headers: dict, family_setup):
    """测试完成家务获得钻石"""
    # Get initial points balance
    user_response = await client.get("/api/v1/users/me", headers=auth_headers)
    initial_points = user_response.json()["data"]["points_balance"]
    
    # Create a chore
    create_response = await client.post(
        "/api/v1/chores",
        headers=auth_headers,
        json={"name": "洗碗", "points_reward": 5, "recurrence": "once"}
    )
    chore_id = create_response.json()["data"]["id"]
    
    # Complete the chore
    complete_response = await client.post(
        f"/api/v1/chores/{chore_id}/complete",
        headers=auth_headers
    )
    
    assert complete_response.status_code == 200
    data = complete_response.json()
    assert data["success"] is True
    assert data["data"]["points_earned"] == 5
    assert "钻石" in data["message"]
    
    # Verify points balance increased
    user_response = await client.get("/api/v1/users/me", headers=auth_headers)
    new_points = user_response.json()["data"]["points_balance"]
    assert new_points == initial_points + 5


@pytest.mark.asyncio
async def test_complete_chore_creates_transaction(client: AsyncClient, auth_headers: dict, family_setup):
    """测试完成家务创建钻石流水记录"""
    # Create and complete a chore
    create_response = await client.post(
        "/api/v1/chores",
        headers=auth_headers,
        json={"name": "测试任务", "points_reward": 10, "recurrence": "once"}
    )
    chore_id = create_response.json()["data"]["id"]
    
    await client.post(f"/api/v1/chores/{chore_id}/complete", headers=auth_headers)
    
    # Check transactions
    transactions_response = await client.get(
        "/api/v1/users/me/transactions",
        headers=auth_headers
    )
    
    data = transactions_response.json()
    assert data["success"] is True
    # Should have at least one transaction
    assert len(data["data"]["items"]) >= 1
    # Latest transaction should be the chore completion
    latest = data["data"]["items"][0]
    assert latest["type"] == "chore"
    assert latest["amount"] == 10


@pytest.mark.asyncio
async def test_complete_inactive_chore_fails(client: AsyncClient, auth_headers: dict, family_setup):
    """测试完成已停用的家务失败"""
    # Create a chore
    create_response = await client.post(
        "/api/v1/chores",
        headers=auth_headers,
        json={"name": "停用任务", "points_reward": 5}
    )
    chore_id = create_response.json()["data"]["id"]
    
    # Deactivate it
    await client.put(
        f"/api/v1/chores/{chore_id}",
        headers=auth_headers,
        json={"is_active": False}
    )
    
    # Try to complete
    response = await client.post(
        f"/api/v1/chores/{chore_id}/complete",
        headers=auth_headers
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_complete_once_chore_deactivates(client: AsyncClient, auth_headers: dict, family_setup):
    """测试完成一次性任务后自动停用"""
    # Create a one-time chore
    create_response = await client.post(
        "/api/v1/chores",
        headers=auth_headers,
        json={"name": "一次性任务", "points_reward": 15, "recurrence": "once"}
    )
    chore_id = create_response.json()["data"]["id"]
    
    # Complete it
    await client.post(f"/api/v1/chores/{chore_id}/complete", headers=auth_headers)
    
    # Check that it's now inactive
    chores_response = await client.get(
        "/api/v1/chores",
        headers=auth_headers,
        params={"is_active": False}
    )
    
    inactive_ids = [c["id"] for c in chores_response.json()["data"]]
    assert chore_id in inactive_ids


# ============== Chore History Tests ==============

@pytest.mark.asyncio
async def test_get_chore_history(client: AsyncClient, auth_headers: dict, family_setup):
    """测试获取家务完成历史"""
    # Create and complete multiple chores
    for i in range(3):
        create_response = await client.post(
            "/api/v1/chores",
            headers=auth_headers,
            json={"name": f"任务{i}", "points_reward": 5, "recurrence": "daily"}
        )
        chore_id = create_response.json()["data"]["id"]
        await client.post(f"/api/v1/chores/{chore_id}/complete", headers=auth_headers)
    
    # Get history
    response = await client.get(
        "/api/v1/chores/history",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["items"]) >= 3


@pytest.mark.asyncio
async def test_get_chore_history_pagination(client: AsyncClient, auth_headers: dict, family_setup):
    """测试家务历史分页"""
    # Create and complete multiple chores
    for i in range(5):
        create_response = await client.post(
            "/api/v1/chores",
            headers=auth_headers,
            json={"name": f"分页任务{i}", "points_reward": 2, "recurrence": "daily"}
        )
        chore_id = create_response.json()["data"]["id"]
        await client.post(f"/api/v1/chores/{chore_id}/complete", headers=auth_headers)
    
    # Get first page with small page size
    response = await client.get(
        "/api/v1/chores/history",
        headers=auth_headers,
        params={"page": 1, "page_size": 2}
    )
    
    data = response.json()
    assert len(data["data"]["items"]) == 2
    assert data["data"]["total"] >= 5


# ============== Recurring Chore Tests ==============

@pytest.mark.asyncio
async def test_daily_chore_stays_active_after_complete(client: AsyncClient, auth_headers: dict, family_setup):
    """测试每日任务完成后仍然活跃"""
    # Create a daily chore
    create_response = await client.post(
        "/api/v1/chores",
        headers=auth_headers,
        json={"name": "每日任务", "points_reward": 3, "recurrence": "daily"}
    )
    chore_id = create_response.json()["data"]["id"]
    
    # Complete it
    await client.post(f"/api/v1/chores/{chore_id}/complete", headers=auth_headers)
    
    # Check it's still active (unlike "once" type)
    chores_response = await client.get(
        "/api/v1/chores",
        headers=auth_headers,
        params={"is_active": True}
    )
    
    active_ids = [c["id"] for c in chores_response.json()["data"]]
    assert chore_id in active_ids


@pytest.mark.asyncio
async def test_weekly_chore_creation(client: AsyncClient, auth_headers: dict, family_setup):
    """测试创建每周任务"""
    response = await client.post(
        "/api/v1/chores",
        headers=auth_headers,
        json={
            "name": "每周大扫除",
            "points_reward": 20,
            "recurrence": "weekly",
            "description": "全屋清洁"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["recurrence"] == "weekly"


@pytest.mark.asyncio
async def test_monthly_chore_creation(client: AsyncClient, auth_headers: dict, family_setup):
    """测试创建每月任务"""
    response = await client.post(
        "/api/v1/chores",
        headers=auth_headers,
        json={
            "name": "月度整理",
            "points_reward": 50,
            "recurrence": "monthly"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["recurrence"] == "monthly"
