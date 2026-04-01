"""
Tests for family management endpoints
"""
import pytest
from httpx import AsyncClient


@pytest.fixture
async def auth_headers(client: AsyncClient):
    """Create a user and return auth headers"""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "familyuser",
            "email": "family@example.com",
            "password": "testpassword123"
        }
    )
    
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "family@example.com",
            "password": "testpassword123"
        }
    )
    data = response.json()
    token = data["data"]["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def second_user_headers(client: AsyncClient):
    """Create a second user and return auth headers"""
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "seconduser",
            "email": "second@example.com",
            "password": "testpassword123"
        }
    )
    
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "second@example.com",
            "password": "testpassword123"
        }
    )
    data = response.json()
    token = data["data"]["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


# ============== Create Family Tests ==============

@pytest.mark.asyncio
async def test_create_family(client: AsyncClient, auth_headers: dict):
    """Test creating a new family"""
    response = await client.post(
        "/api/v1/families",
        headers=auth_headers,
        json={"name": "Smith Family"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "Smith Family"
    assert len(data["data"]["invite_code"]) == 8


@pytest.mark.asyncio
async def test_create_family_already_in_family(client: AsyncClient, auth_headers: dict):
    """Test creating a family when user is already in one"""
    # Create first family
    await client.post(
        "/api/v1/families",
        headers=auth_headers,
        json={"name": "First Family"}
    )
    
    # Try to create second family
    response = await client.post(
        "/api/v1/families",
        headers=auth_headers,
        json={"name": "Second Family"}
    )
    
    assert response.status_code == 400
    assert "already in a family" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_family_sets_admin_role(client: AsyncClient, auth_headers: dict):
    """Test that family creator becomes admin"""
    # Create family
    await client.post(
        "/api/v1/families",
        headers=auth_headers,
        json={"name": "Admin Test Family"}
    )
    
    # Get family members
    response = await client.get(
        "/api/v1/families/members",
        headers=auth_headers
    )
    
    data = response.json()
    assert data["data"][0]["role"] == "admin"


# ============== Join Family Tests ==============

@pytest.mark.asyncio
async def test_join_family(client: AsyncClient, auth_headers: dict, second_user_headers: dict):
    """Test joining a family with invite code"""
    # First user creates family
    create_response = await client.post(
        "/api/v1/families",
        headers=auth_headers,
        json={"name": "Join Test Family"}
    )
    invite_code = create_response.json()["data"]["invite_code"]
    
    # Second user joins family
    response = await client.post(
        "/api/v1/families/join",
        headers=second_user_headers,
        json={"invite_code": invite_code}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["name"] == "Join Test Family"
    assert len(data["data"]["members"]) == 2


@pytest.mark.asyncio
async def test_join_family_invalid_code(client: AsyncClient, auth_headers: dict):
    """Test joining with invalid invite code"""
    response = await client.post(
        "/api/v1/families/join",
        headers=auth_headers,
        json={"invite_code": "INVALID1"}
    )
    
    assert response.status_code == 404
    assert "invalid invite code" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_join_family_already_in_family(client: AsyncClient, auth_headers: dict, second_user_headers: dict):
    """Test joining a family when already in one"""
    # First user creates family
    await client.post(
        "/api/v1/families",
        headers=auth_headers,
        json={"name": "Family 1"}
    )
    
    # Second user creates their own family
    await client.post(
        "/api/v1/families",
        headers=second_user_headers,
        json={"name": "Family 2"}
    )
    
    # Second user tries to join first user's family (should fail)
    # Need to get invite code first
    family_response = await client.get(
        "/api/v1/families/me",
        headers=auth_headers
    )
    invite_code = family_response.json()["data"]["invite_code"]
    
    response = await client.post(
        "/api/v1/families/join",
        headers=second_user_headers,
        json={"invite_code": invite_code}
    )
    
    assert response.status_code == 400
    assert "already in a family" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_joined_member_is_not_admin(client: AsyncClient, auth_headers: dict, second_user_headers: dict):
    """Test that joined member gets member role, not admin"""
    # First user creates family
    create_response = await client.post(
        "/api/v1/families",
        headers=auth_headers,
        json={"name": "Role Test Family"}
    )
    invite_code = create_response.json()["data"]["invite_code"]
    
    # Second user joins
    await client.post(
        "/api/v1/families/join",
        headers=second_user_headers,
        json={"invite_code": invite_code}
    )
    
    # Check second user's role
    user_response = await client.get(
        "/api/v1/users/me",
        headers=second_user_headers
    )
    
    assert user_response.json()["data"]["role"] == "member"


# ============== Get Family Tests ==============

@pytest.mark.asyncio
async def test_get_my_family(client: AsyncClient, auth_headers: dict):
    """Test getting current user's family"""
    # Create family
    await client.post(
        "/api/v1/families",
        headers=auth_headers,
        json={"name": "My Family"}
    )
    
    # Get family
    response = await client.get(
        "/api/v1/families/me",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["name"] == "My Family"
    assert data["data"]["members"] is not None


@pytest.mark.asyncio
async def test_get_my_family_not_in_family(client: AsyncClient, auth_headers: dict):
    """Test getting family when user is not in one"""
    response = await client.get(
        "/api/v1/families/me",
        headers=auth_headers
    )
    
    assert response.status_code == 404


# ============== Get Members Tests ==============

@pytest.mark.asyncio
async def test_get_family_members(client: AsyncClient, auth_headers: dict, second_user_headers: dict):
    """Test getting family members"""
    # Create family
    create_response = await client.post(
        "/api/v1/families",
        headers=auth_headers,
        json={"name": "Members Test Family"}
    )
    invite_code = create_response.json()["data"]["invite_code"]
    
    # Second user joins
    await client.post(
        "/api/v1/families/join",
        headers=second_user_headers,
        json={"invite_code": invite_code}
    )
    
    # Get members
    response = await client.get(
        "/api/v1/families/members",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    
    # Verify member info
    usernames = [m["username"] for m in data["data"]]
    assert "familyuser" in usernames
    assert "seconduser" in usernames


@pytest.mark.asyncio
async def test_get_members_not_in_family(client: AsyncClient, auth_headers: dict):
    """Test getting members when not in a family"""
    response = await client.get(
        "/api/v1/families/members",
        headers=auth_headers
    )
    
    assert response.status_code == 404


# ============== Invite Code Tests ==============

@pytest.mark.asyncio
async def test_regenerate_invite_code(client: AsyncClient, auth_headers: dict):
    """Test regenerating invite code"""
    # Create family
    create_response = await client.post(
        "/api/v1/families",
        headers=auth_headers,
        json={"name": "Invite Code Test"}
    )
    old_code = create_response.json()["data"]["invite_code"]
    
    # Regenerate code
    response = await client.put(
        "/api/v1/families/invite-code",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    new_code = response.json()["data"]["invite_code"]
    assert new_code != old_code
    assert len(new_code) == 8


@pytest.mark.asyncio
async def test_regenerate_invite_code_not_admin(client: AsyncClient, auth_headers: dict, second_user_headers: dict):
    """Test that non-admin cannot regenerate invite code"""
    # Create family
    create_response = await client.post(
        "/api/v1/families",
        headers=auth_headers,
        json={"name": "Admin Only Test"}
    )
    invite_code = create_response.json()["data"]["invite_code"]
    
    # Second user joins
    await client.post(
        "/api/v1/families/join",
        headers=second_user_headers,
        json={"invite_code": invite_code}
    )
    
    # Second user tries to regenerate code (should fail)
    response = await client.put(
        "/api/v1/families/invite-code",
        headers=second_user_headers
    )
    
    assert response.status_code == 403
    assert "admin" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_old_invite_code_invalid_after_regenerate(client: AsyncClient, auth_headers: dict):
    """Test that old invite code is invalid after regeneration"""
    # Create family
    create_response = await client.post(
        "/api/v1/families",
        headers=auth_headers,
        json={"name": "Code Invalidation Test"}
    )
    old_code = create_response.json()["data"]["invite_code"]
    
    # Regenerate code
    await client.put(
        "/api/v1/families/invite-code",
        headers=auth_headers
    )
    
    # Register and login new user
    await client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "testpassword123"
        }
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "new@example.com",
            "password": "testpassword123"
        }
    )
    new_token = login_response.json()["data"]["access_token"]
    new_headers = {"Authorization": f"Bearer {new_token}"}
    
    # Try to join with old code (should fail)
    response = await client.post(
        "/api/v1/families/join",
        headers=new_headers,
        json={"invite_code": old_code}
    )
    
    assert response.status_code == 404

