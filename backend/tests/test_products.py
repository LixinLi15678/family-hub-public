"""
Tests for point shop products endpoints
"""
import pytest
from httpx import AsyncClient


@pytest.fixture
async def auth_headers(client: AsyncClient):
    """Create a user and return auth headers"""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "shopuser",
            "email": "shop@example.com",
            "password": "testpassword123"
        }
    )
    
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "shop@example.com",
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
        json={"name": "Shop Test Family"}
    )
    return response.json()["data"]


@pytest.fixture
async def user_with_points(client: AsyncClient, auth_headers: dict, family_setup):
    """Give user some points by completing chores"""
    # Create and complete multiple chores to get points
    for i in range(5):
        create_response = await client.post(
            "/api/v1/chores",
            headers=auth_headers,
            json={"name": f"赚钻石任务{i}", "points_reward": 20, "recurrence": "daily"}
        )
        chore_id = create_response.json()["data"]["id"]
        await client.post(f"/api/v1/chores/{chore_id}/complete", headers=auth_headers)
    
    # Now user should have 100 points
    return auth_headers


# ============== Create Product Tests ==============

@pytest.mark.asyncio
async def test_create_product(client: AsyncClient, auth_headers: dict, family_setup):
    """测试上架商品"""
    response = await client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={
            "name": "电影票",
            "description": "一张电影票兑换券",
            "points_price": 50
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "电影票"
    assert data["data"]["points_price"] == 50
    assert data["data"]["is_active"] is True


@pytest.mark.asyncio
async def test_create_product_with_stock(client: AsyncClient, auth_headers: dict, family_setup):
    """测试上架限量商品"""
    response = await client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={
            "name": "限量玩具",
            "points_price": 100,
            "stock": 5
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["stock"] == 5


@pytest.mark.asyncio
async def test_create_product_without_family(client: AsyncClient, auth_headers: dict):
    """测试未加入家庭时上架商品"""
    response = await client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={
            "name": "测试商品",
            "points_price": 10
        }
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_product_points_price_too_high(client: AsyncClient, auth_headers: dict, family_setup):
    """points_price should be <= 50000"""
    response = await client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={
            "name": "超高钻石商品",
            "points_price": 50001
        }
    )
    assert response.status_code == 422


# ============== Get Products Tests ==============

@pytest.mark.asyncio
async def test_get_products(client: AsyncClient, auth_headers: dict, family_setup):
    """测试获取商品列表"""
    # Create multiple products
    products = [
        {"name": "商品1", "points_price": 10},
        {"name": "商品2", "points_price": 20},
        {"name": "商品3", "points_price": 30}
    ]
    for product in products:
        await client.post("/api/v1/products", headers=auth_headers, json=product)
    
    # Get products
    response = await client.get("/api/v1/products", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 3


@pytest.mark.asyncio
async def test_get_products_filter_active(client: AsyncClient, auth_headers: dict, family_setup):
    """测试只获取活跃商品"""
    # Create a product
    create_response = await client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={"name": "待下架商品", "points_price": 15}
    )
    product_id = create_response.json()["data"]["id"]
    
    # Deactivate it
    await client.delete(f"/api/v1/products/{product_id}", headers=auth_headers)
    
    # Get only active products
    response = await client.get(
        "/api/v1/products",
        headers=auth_headers,
        params={"is_active": True}
    )
    
    data = response.json()
    for product in data["data"]:
        assert product["is_active"] is True


# ============== Update Product Tests ==============

@pytest.mark.asyncio
async def test_update_product(client: AsyncClient, auth_headers: dict, family_setup):
    """测试更新商品"""
    # Create a product
    create_response = await client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={"name": "原始商品", "points_price": 25}
    )
    product_id = create_response.json()["data"]["id"]
    
    # Update it
    response = await client.put(
        f"/api/v1/products/{product_id}",
        headers=auth_headers,
        json={"name": "更新后商品", "points_price": 30}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["name"] == "更新后商品"
    assert data["data"]["points_price"] == 30


@pytest.mark.asyncio
async def test_update_product_not_found(client: AsyncClient, auth_headers: dict, family_setup):
    """测试更新不存在的商品"""
    response = await client.put(
        "/api/v1/products/99999",
        headers=auth_headers,
        json={"name": "不存在"}
    )
    
    assert response.status_code == 404


# ============== Delete Product Tests ==============

@pytest.mark.asyncio
async def test_delete_product(client: AsyncClient, auth_headers: dict, family_setup):
    """测试下架商品（软删除）"""
    # Create a product
    create_response = await client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={"name": "待下架", "points_price": 10}
    )
    product_id = create_response.json()["data"]["id"]
    
    # Delete it
    response = await client.delete(
        f"/api/v1/products/{product_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    
    # Verify it's inactive but still exists
    get_response = await client.get(
        "/api/v1/products",
        headers=auth_headers,
        params={"is_active": False}
    )
    
    inactive_ids = [p["id"] for p in get_response.json()["data"]]
    assert product_id in inactive_ids


# ============== Purchase Product Tests ==============

@pytest.mark.asyncio
async def test_purchase_product(client: AsyncClient, user_with_points: dict, family_setup):
    """测试购买商品"""
    # Create a product
    create_response = await client.post(
        "/api/v1/products",
        headers=user_with_points,
        json={"name": "可购买商品", "points_price": 30}
    )
    product_id = create_response.json()["data"]["id"]
    
    # Get initial points
    user_response = await client.get("/api/v1/users/me", headers=user_with_points)
    initial_points = user_response.json()["data"]["points_balance"]
    
    # Purchase
    response = await client.post(
        f"/api/v1/products/{product_id}/purchase",
        headers=user_with_points
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["points_spent"] == 30
    
    # Verify points deducted
    user_response = await client.get("/api/v1/users/me", headers=user_with_points)
    new_points = user_response.json()["data"]["points_balance"]
    assert new_points == initial_points - 30


@pytest.mark.asyncio
async def test_purchase_insufficient_points(client: AsyncClient, auth_headers: dict, family_setup):
    """测试钻石不足时购买失败"""
    # Create an expensive product
    create_response = await client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={"name": "昂贵商品", "points_price": 9999}
    )
    product_id = create_response.json()["data"]["id"]
    
    # Try to purchase (user has 0 points)
    response = await client.post(
        f"/api/v1/products/{product_id}/purchase",
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "钻石不足" in response.json()["detail"]["error"]["message"]


@pytest.mark.asyncio
async def test_purchase_out_of_stock(client: AsyncClient, user_with_points: dict, family_setup):
    """测试库存不足时购买失败"""
    # Create a product with 1 stock
    create_response = await client.post(
        "/api/v1/products",
        headers=user_with_points,
        json={"name": "限量商品", "points_price": 10, "stock": 1}
    )
    product_id = create_response.json()["data"]["id"]
    
    # First purchase should succeed
    first_purchase = await client.post(
        f"/api/v1/products/{product_id}/purchase",
        headers=user_with_points
    )
    assert first_purchase.status_code == 200
    
    # Second purchase should fail (out of stock)
    second_purchase = await client.post(
        f"/api/v1/products/{product_id}/purchase",
        headers=user_with_points
    )
    assert second_purchase.status_code == 400
    assert "售罄" in second_purchase.json()["detail"]["error"]["message"]


@pytest.mark.asyncio
async def test_purchase_inactive_product(client: AsyncClient, user_with_points: dict, family_setup):
    """测试购买已下架商品失败"""
    # Create and deactivate a product
    create_response = await client.post(
        "/api/v1/products",
        headers=user_with_points,
        json={"name": "已下架商品", "points_price": 10}
    )
    product_id = create_response.json()["data"]["id"]
    
    await client.delete(f"/api/v1/products/{product_id}", headers=user_with_points)
    
    # Try to purchase
    response = await client.post(
        f"/api/v1/products/{product_id}/purchase",
        headers=user_with_points
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_purchase_creates_transaction(client: AsyncClient, user_with_points: dict, family_setup):
    """测试购买创建钻石流水记录"""
    # Create a product
    create_response = await client.post(
        "/api/v1/products",
        headers=user_with_points,
        json={"name": "流水测试商品", "points_price": 15}
    )
    product_id = create_response.json()["data"]["id"]
    
    # Purchase
    await client.post(f"/api/v1/products/{product_id}/purchase", headers=user_with_points)
    
    # Check transactions
    transactions_response = await client.get(
        "/api/v1/users/me/transactions",
        headers=user_with_points
    )
    
    data = transactions_response.json()
    # Find the purchase transaction
    purchase_transactions = [t for t in data["data"]["items"] if t["type"] == "purchase"]
    assert len(purchase_transactions) >= 1
    assert purchase_transactions[0]["amount"] == -15


# ============== My Purchases Tests ==============

@pytest.mark.asyncio
async def test_get_my_purchases(client: AsyncClient, user_with_points: dict, family_setup):
    """测试获取已购商品"""
    # Create and purchase multiple products
    for i in range(3):
        create_response = await client.post(
            "/api/v1/products",
            headers=user_with_points,
            json={"name": f"购买测试{i}", "points_price": 10}
        )
        product_id = create_response.json()["data"]["id"]
        await client.post(f"/api/v1/products/{product_id}/purchase", headers=user_with_points)
    
    # Get my purchases
    response = await client.get("/api/v1/users/me/purchases", headers=user_with_points)
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) >= 3


@pytest.mark.asyncio
async def test_use_purchased_product(client: AsyncClient, user_with_points: dict, family_setup):
    """测试使用已购商品"""
    # Create and purchase a product
    create_response = await client.post(
        "/api/v1/products",
        headers=user_with_points,
        json={"name": "可使用商品", "points_price": 10}
    )
    product_id = create_response.json()["data"]["id"]
    
    purchase_response = await client.post(
        f"/api/v1/products/{product_id}/purchase",
        headers=user_with_points
    )
    purchase_id = purchase_response.json()["data"]["id"]
    
    # Use the product
    response = await client.patch(
        f"/api/v1/users/purchases/{purchase_id}/use",
        headers=user_with_points
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["use_count"] == 1
    assert data["data"]["used_at"] is not None


@pytest.mark.asyncio
async def test_use_product_multiple_times(client: AsyncClient, user_with_points: dict, family_setup):
    """测试多次使用商品"""
    # Create and purchase a product
    create_response = await client.post(
        "/api/v1/products",
        headers=user_with_points,
        json={"name": "多次使用商品", "points_price": 10}
    )
    product_id = create_response.json()["data"]["id"]
    
    purchase_response = await client.post(
        f"/api/v1/products/{product_id}/purchase",
        headers=user_with_points
    )
    purchase_id = purchase_response.json()["data"]["id"]
    
    # Use multiple times
    for _ in range(3):
        await client.patch(
            f"/api/v1/users/purchases/{purchase_id}/use",
            headers=user_with_points
        )
    
    # Get my purchases and check use count
    purchases_response = await client.get("/api/v1/users/me/purchases", headers=user_with_points)
    purchases = purchases_response.json()["data"]
    
    target_purchase = next(p for p in purchases if p["id"] == purchase_id)
    assert target_purchase["use_count"] == 3


# ============== Point Transactions Tests ==============

@pytest.mark.asyncio
async def test_get_point_transactions(client: AsyncClient, user_with_points: dict, family_setup):
    """测试获取钻石流水"""
    response = await client.get(
        "/api/v1/users/me/transactions",
        headers=user_with_points
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # Should have transactions from earning points
    assert len(data["data"]["items"]) >= 1


@pytest.mark.asyncio
async def test_transactions_include_chore_and_purchase(client: AsyncClient, user_with_points: dict, family_setup):
    """测试流水包含家务和购买记录"""
    # Create and purchase a product
    create_response = await client.post(
        "/api/v1/products",
        headers=user_with_points,
        json={"name": "流水测试", "points_price": 10}
    )
    product_id = create_response.json()["data"]["id"]
    await client.post(f"/api/v1/products/{product_id}/purchase", headers=user_with_points)
    
    # Get transactions
    response = await client.get(
        "/api/v1/users/me/transactions",
        headers=user_with_points
    )
    
    data = response.json()
    transaction_types = set(t["type"] for t in data["data"]["items"])
    
    # Should have both chore (income) and purchase (expense) transactions
    assert "chore" in transaction_types
    assert "purchase" in transaction_types


@pytest.mark.asyncio
async def test_transactions_pagination(client: AsyncClient, user_with_points: dict, family_setup):
    """测试钻石流水分页"""
    response = await client.get(
        "/api/v1/users/me/transactions",
        headers=user_with_points,
        params={"page": 1, "page_size": 3}
    )
    
    data = response.json()
    assert len(data["data"]["items"]) <= 3
    assert "total" in data["data"]
    assert "total_pages" in data["data"]
