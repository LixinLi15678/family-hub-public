"""
Tests for shopping list endpoints
"""
import pytest
from httpx import AsyncClient


@pytest.fixture
async def auth_headers(client: AsyncClient):
    """Create a user and return auth headers"""
    # Register user
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )
    
    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
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
        json={"name": "Test Family"}
    )
    return response.json()["data"]


# ============== Shopping Lists Tests ==============

@pytest.mark.asyncio
async def test_create_shopping_list(client: AsyncClient, auth_headers: dict, family_setup):
    """Test creating a shopping list"""
    response = await client.post(
        "/api/v1/shopping/lists",
        headers=auth_headers,
        json={"name": "Weekly Groceries"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Weekly Groceries"
    assert data["data"]["is_active"] is True


@pytest.mark.asyncio
async def test_create_shopping_list_without_family(client: AsyncClient, auth_headers: dict):
    """Test creating a shopping list without being in a family"""
    response = await client.post(
        "/api/v1/shopping/lists",
        headers=auth_headers,
        json={"name": "My List"}
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_shopping_lists(client: AsyncClient, auth_headers: dict, family_setup):
    """Test getting all shopping lists"""
    # Create two lists
    await client.post(
        "/api/v1/shopping/lists",
        headers=auth_headers,
        json={"name": "List 1"}
    )
    await client.post(
        "/api/v1/shopping/lists",
        headers=auth_headers,
        json={"name": "List 2"}
    )
    
    # Get lists
    response = await client.get(
        "/api/v1/shopping/lists",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 2


@pytest.mark.asyncio
async def test_get_shopping_list_by_id(client: AsyncClient, auth_headers: dict, family_setup):
    """Test getting a specific shopping list"""
    # Create a list
    create_response = await client.post(
        "/api/v1/shopping/lists",
        headers=auth_headers,
        json={"name": "Test List"}
    )
    list_id = create_response.json()["data"]["id"]
    
    # Get the list
    response = await client.get(
        f"/api/v1/shopping/lists/{list_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["name"] == "Test List"


@pytest.mark.asyncio
async def test_delete_shopping_list(client: AsyncClient, auth_headers: dict, family_setup):
    """Test deleting a shopping list"""
    # Create a list
    create_response = await client.post(
        "/api/v1/shopping/lists",
        headers=auth_headers,
        json={"name": "To Delete"}
    )
    list_id = create_response.json()["data"]["id"]
    
    # Delete the list
    response = await client.delete(
        f"/api/v1/shopping/lists/{list_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    
    # Verify deletion
    get_response = await client.get(
        f"/api/v1/shopping/lists/{list_id}",
        headers=auth_headers
    )
    assert get_response.status_code == 404


# ============== Shopping Items Tests ==============

@pytest.mark.asyncio
async def test_add_shopping_item(client: AsyncClient, auth_headers: dict, family_setup):
    """Test adding an item to a shopping list"""
    # Create a list first
    list_response = await client.post(
        "/api/v1/shopping/lists",
        headers=auth_headers,
        json={"name": "Grocery List"}
    )
    list_id = list_response.json()["data"]["id"]
    
    # Add an item
    response = await client.post(
        "/api/v1/shopping/items",
        headers=auth_headers,
        json={
            "list_id": list_id,
            "name": "Milk",
            "quantity": 2,
            "unit": "gallons"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Milk"
    assert data["data"]["quantity"] == 2
    assert data["data"]["is_checked"] is False


@pytest.mark.asyncio
async def test_add_shopping_item_with_note(client: AsyncClient, auth_headers: dict, family_setup):
    """Test adding an item with a note"""
    list_response = await client.post(
        "/api/v1/shopping/lists",
        headers=auth_headers,
        json={"name": "Shopping List"}
    )
    list_id = list_response.json()["data"]["id"]
    
    response = await client.post(
        "/api/v1/shopping/items",
        headers=auth_headers,
        json={
            "list_id": list_id,
            "name": "Eggs",
            "quantity": 1,
            "note": "Get organic free-range"
        }
    )
    
    assert response.status_code == 200
    assert response.json()["data"]["note"] == "Get organic free-range"


@pytest.mark.asyncio
async def test_check_shopping_item(client: AsyncClient, auth_headers: dict, family_setup):
    """Test checking/unchecking a shopping item"""
    # Create list and item
    list_response = await client.post(
        "/api/v1/shopping/lists",
        headers=auth_headers,
        json={"name": "Check Test List"}
    )
    list_id = list_response.json()["data"]["id"]
    
    item_response = await client.post(
        "/api/v1/shopping/items",
        headers=auth_headers,
        json={
            "list_id": list_id,
            "name": "Bread"
        }
    )
    item_id = item_response.json()["data"]["id"]
    
    # Check the item
    check_response = await client.patch(
        f"/api/v1/shopping/items/{item_id}/check",
        headers=auth_headers
    )
    
    assert check_response.status_code == 200
    data = check_response.json()
    assert data["data"]["is_checked"] is True
    assert data["data"]["checked_by"] is not None
    assert data["data"]["checked_at"] is not None
    
    # Uncheck the item
    uncheck_response = await client.patch(
        f"/api/v1/shopping/items/{item_id}/check",
        headers=auth_headers
    )
    
    assert uncheck_response.status_code == 200
    assert uncheck_response.json()["data"]["is_checked"] is False


@pytest.mark.asyncio
async def test_delete_shopping_item(client: AsyncClient, auth_headers: dict, family_setup):
    """Test deleting a shopping item"""
    # Create list and item
    list_response = await client.post(
        "/api/v1/shopping/lists",
        headers=auth_headers,
        json={"name": "Delete Item Test"}
    )
    list_id = list_response.json()["data"]["id"]
    
    item_response = await client.post(
        "/api/v1/shopping/items",
        headers=auth_headers,
        json={
            "list_id": list_id,
            "name": "To Delete"
        }
    )
    item_id = item_response.json()["data"]["id"]
    
    # Delete the item
    response = await client.delete(
        f"/api/v1/shopping/items/{item_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "商品已删除"


@pytest.mark.asyncio
async def test_get_shopping_list_items(client: AsyncClient, auth_headers: dict, family_setup):
    """Test getting all items in a shopping list"""
    # Create list
    list_response = await client.post(
        "/api/v1/shopping/lists",
        headers=auth_headers,
        json={"name": "Full List"}
    )
    list_id = list_response.json()["data"]["id"]
    
    # Add multiple items
    items = ["Apples", "Bananas", "Oranges"]
    for item in items:
        await client.post(
            "/api/v1/shopping/items",
            headers=auth_headers,
            json={"list_id": list_id, "name": item}
        )
    
    # Get items
    response = await client.get(
        f"/api/v1/shopping/lists/{list_id}/items",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 3


@pytest.mark.asyncio
async def test_update_shopping_item(client: AsyncClient, auth_headers: dict, family_setup):
    """Test updating a shopping item"""
    # Create list and item
    list_response = await client.post(
        "/api/v1/shopping/lists",
        headers=auth_headers,
        json={"name": "Update Test"}
    )
    list_id = list_response.json()["data"]["id"]
    
    item_response = await client.post(
        "/api/v1/shopping/items",
        headers=auth_headers,
        json={
            "list_id": list_id,
            "name": "Old Name",
            "quantity": 1
        }
    )
    item_id = item_response.json()["data"]["id"]
    version = item_response.json()["data"]["version"]
    
    # Update the item
    response = await client.patch(
        f"/api/v1/shopping/items/{item_id}",
        headers=auth_headers,
        json={
            "name": "New Name",
            "quantity": 5,
            "version": version
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["name"] == "New Name"
    assert data["data"]["quantity"] == 5


@pytest.mark.asyncio
async def test_update_shopping_item_conflict(client: AsyncClient, auth_headers: dict, family_setup):
    """Test optimistic locking conflict on update"""
    # Create list and item
    list_response = await client.post(
        "/api/v1/shopping/lists",
        headers=auth_headers,
        json={"name": "Conflict Test"}
    )
    list_id = list_response.json()["data"]["id"]
    
    item_response = await client.post(
        "/api/v1/shopping/items",
        headers=auth_headers,
        json={
            "list_id": list_id,
            "name": "Test Item"
        }
    )
    item_id = item_response.json()["data"]["id"]
    
    # Try to update with wrong version
    response = await client.patch(
        f"/api/v1/shopping/items/{item_id}",
        headers=auth_headers,
        json={
            "name": "Updated Name",
            "version": 999  # Wrong version
        }
    )
    
    assert response.status_code == 409  # Conflict


# ============== Stores Tests ==============

@pytest.mark.asyncio
async def test_create_store(client: AsyncClient, auth_headers: dict, family_setup):
    """Test creating a store"""
    response = await client.post(
        "/api/v1/shopping/stores",
        headers=auth_headers,
        json={
            "name": "Costco",
            "icon": "🛒"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["name"] == "Costco"
    assert data["data"]["icon"] == "🛒"


@pytest.mark.asyncio
async def test_get_stores(client: AsyncClient, auth_headers: dict, family_setup):
    """Test getting all stores"""
    # Create stores
    stores = ["Costco", "Weee", "Sprout"]
    for store in stores:
        await client.post(
            "/api/v1/shopping/stores",
            headers=auth_headers,
            json={"name": store}
        )
    
    # Get stores
    response = await client.get(
        "/api/v1/shopping/stores",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 3

