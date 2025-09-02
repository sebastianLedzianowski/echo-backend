import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth import auth_service
from src.tests.conftest import login_user_confirmed_true_and_hash_password


# ================== READ ME ==================
@pytest.mark.asyncio
async def test_read_users_me_success(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Create and login user
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    response = await client.get(
        "/api/users/me/",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == user.username
    assert data["email"] == user.email
    assert "password" not in data


@pytest.mark.asyncio
async def test_read_users_me_no_token(client: AsyncClient):
    response = await client.get("/api/users/me/")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.asyncio
async def test_read_users_me_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/users/me/",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
    assert "Nieprawidłowe dane uwierzytelniające" in response.json()["detail"]


# ================== UPDATE ME ==================
@pytest.mark.asyncio
async def test_update_me_success(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Create and login user
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Update data
    new_data = {
        "full_name": "New Name",
        "email": "newemail@example.com"
    }

    response = await client.patch(
        "/api/users/me/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=new_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == new_data["full_name"]
    assert data["email"] == new_data["email"]
    assert data["username"] == user.username


@pytest.mark.asyncio
async def test_update_me_partial(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Create and login user
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Update only full_name
    new_data = {"full_name": "New Name"}

    response = await client.patch(
        "/api/users/me/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=new_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == new_data["full_name"]
    assert data["email"] == user.email
    assert data["username"] == user.username


@pytest.mark.asyncio
async def test_update_me_no_token(client: AsyncClient):
    response = await client.patch(
        "/api/users/me/",
        json={"full_name": "New Name"}
    )
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_me_invalid_token(client: AsyncClient):
    response = await client.patch(
        "/api/users/me/",
        headers={"Authorization": "Bearer invalid_token"},
        json={"full_name": "New Name"}
    )
    assert response.status_code == 401
    assert "Nieprawidłowe dane uwierzytelniające" in response.json()["detail"]


# ================== CHANGE PASSWORD ==================
@pytest.mark.asyncio
async def test_change_password_success(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Create and login user
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Change password
    password_data = {
        "old_password": user_data.password,
        "new_password": "NewStrongPass123!"
    }

    response = await client.patch(
        "/api/users/me/password/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=password_data
    )
    assert response.status_code == 200
    assert "Hasło zostało zmienione" in response.json()["detail"]

    # Verify can login with new password
    login_response = await client.post(
        "/api/auth/login",
        data={"username": user.username, "password": "NewStrongPass123!"}
    )
    assert login_response.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_old_password(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Create and login user
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Try to change password with wrong old password
    password_data = {
        "old_password": "WrongPass123!",
        "new_password": "NewStrongPass123!"
    }

    response = await client.patch(
        "/api/users/me/password/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=password_data
    )
    assert response.status_code == 400
    assert "Nieprawidłowe stare hasło" in response.json()["detail"]


@pytest.mark.asyncio
async def test_change_password_weak_new_password(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Create and login user
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Try to change to weak password
    password_data = {
        "old_password": user_data.password,
        "new_password": "weak"
    }

    response = await client.patch(
        "/api/users/me/password/",
        headers={"Authorization": f"Bearer {access_token}"},
        json=password_data
    )
    assert response.status_code in (400, 422)
    error = response.json()["detail"][0]
    assert error["type"] == "string_too_short"
    assert "String should have at least" in error["msg"]


@pytest.mark.asyncio
async def test_change_password_no_token(client: AsyncClient):
    response = await client.patch(
        "/api/users/me/password/",
        json={"old_password": "old", "new_password": "new"}
    )
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


# ================== DELETE ACCOUNT ==================
@pytest.mark.asyncio
async def test_delete_account_success(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Create and login user
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Delete account
    response = await client.delete(
        f"/api/users/me/?password={user_data.password}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "Konto zostało usunięte" in response.json()["detail"]

    # Verify user cannot login anymore
    login_response = await client.post(
        "/api/auth/login",
        data={"username": user.username, "password": user_data.password}
    )
    assert login_response.status_code == 401


@pytest.mark.asyncio
async def test_delete_account_wrong_password(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Create and login user
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Try to delete account with wrong password
    response = await client.delete(
        "/api/users/me/?password=WrongPass123!",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 400
    assert "Nieprawidłowe hasło" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_account_no_token(client: AsyncClient):
    response = await client.delete(
        "/api/users/me/?password=password123"
    )
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_account_invalid_token(client: AsyncClient):
    response = await client.delete(
        "/api/users/me/?password=password123",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
    assert "Nieprawidłowe dane uwierzytelniające" in response.json()["detail"]