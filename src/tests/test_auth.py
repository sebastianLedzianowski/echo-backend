import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from src.services.auth import auth_service
from src.repository import users as repository_users
from src.tests.conftest import (
    login_user_confirmed_true_and_hash_password,
    create_user_db
)


# ================== SIGNUP ==================
@pytest.mark.asyncio
async def test_signup_success(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    response = await client.post(
        "/api/auth/signup",
        json=user_data.dict()
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["username"] == user_data.username
    assert "detail" in body


@pytest.mark.asyncio
async def test_signup_duplicate_username(client: AsyncClient, db_session: AsyncSession, user_data):
    await repository_users.create_user(user_data, db_session)
    response = await client.post("/api/auth/signup", json=user_data.dict())
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient, db_session: AsyncSession, user_data):
    user = user_data
    await repository_users.create_user(user, db_session)
    user2 = user_data
    user2.username = "otheruser"
    response = await client.post("/api/auth/signup", json=user2.dict())
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_signup_invalid_password(client: AsyncClient, user_data):
    user = user_data
    user.password = "123"
    response = await client.post("/api/auth/signup", json=user.dict())
    assert response.status_code in (400, 422)


# ================== LOGIN ==================
@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession, user_data):
    await login_user_confirmed_true_and_hash_password(user_data, db_session)
    response = await client.post("/api/auth/login", data={"username": user_data.username, "password": user_data.password})
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body and "refresh_token" in body


@pytest.mark.asyncio
async def test_login_unconfirmed_email(client: AsyncClient, db_session: AsyncSession, user_data):
    # Create user with hashed password but don't confirm email
    hashed_password = auth_service.get_password_hash(user_data.password)
    user = await create_user_db(user_data, db_session)
    user.password = hashed_password
    user.confirmed = False
    await db_session.commit()
    
    response = await client.post("/api/auth/login", data={"username": user_data.username, "password": user_data.password})
    assert response.status_code == 401
    assert "nie został potwierdzony" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_invalid_username(client: AsyncClient):
    response = await client.post("/api/auth/login", data={"username": "nouser", "password": "pass"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, db_session: AsyncSession, user_data):
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    response = await client.post("/api/auth/login", data={"username": user.username, "password": "wrongpass"})
    assert response.status_code == 401


# ================== REFRESH TOKEN ==================
@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient, db_session: AsyncSession, user_data):
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    refresh_token = auth_service.create_token(user.username, scope="refresh_token")
    user.refresh_token = refresh_token
    await db_session.commit()

    response = await client.get("/api/auth/refresh_token", headers={"Authorization": f"Bearer {refresh_token}"})
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body and "refresh_token" in body


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    response = await client.get("/api/auth/refresh_token", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == 401


# ================== CONFIRM EMAIL ==================
@pytest.mark.asyncio
async def test_confirm_email_success(client: AsyncClient, db_session: AsyncSession, user_data):
    user = await create_user_db(user_data, db_session)
    token = auth_service.create_token(user.email, scope="email_confirm")
    response = await client.get(f"/api/auth/confirmed_email/{token}")
    assert response.status_code == 200
    assert "E-mail potwierdzony" in response.json()["message"]


@pytest.mark.asyncio
async def test_confirm_email_invalid(client: AsyncClient):
    response = await client.get("/api/auth/confirmed_email/invalidtoken")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_request_email_confirmation(client: AsyncClient, db_session: AsyncSession, user_data):
    await create_user_db(user_data, db_session)
    user_data.confirmed = False
    response = await client.post("/api/auth/request_email", json={"email": user_data.email})
    assert response.status_code == 200
    assert "Wysłano" in response.json()["message"]


# ================== PASSWORD RESET ==================
@pytest.mark.asyncio
async def test_request_password_reset(client: AsyncClient, db_session: AsyncSession, user_data):
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    response = await client.post("/api/auth/request_password_reset", json={"email": user.email})
    assert response.status_code == 200
    assert "resetu hasła" in response.json()["message"]


@pytest.mark.asyncio
async def test_reset_password_success(client: AsyncClient, db_session: AsyncSession, user_data):
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    token = auth_service.create_token(user.email, scope="reset_password")
    response = await client.post("/api/auth/reset-password", json={"token": token, "new_password": "NewStrongPass123!"})
    assert response.status_code == 200
    assert "zaktualizowane" in response.json()["detail"]


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client: AsyncClient):
    response = await client.post("/api/auth/reset-password", json={"token": "invalidtoken", "new_password": "NewStrongPass123!"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_reset_password_weak_password(client: AsyncClient, db_session: AsyncSession, user_data):
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    token = auth_service.create_token(user.email, scope="reset_password")
    response = await client.post("/api/auth/reset-password", json={"token": token, "new_password": "123"})
    assert response.status_code in (400, 422)


# ================== PASSWORD VALIDATION ==================
def test_password_validation_too_short():
    with pytest.raises(HTTPException) as exc_info:
        auth_service.validate_password("Abc1!")
    assert exc_info.value.status_code == 400
    assert "co najmniej 8 znaków" in exc_info.value.detail


def test_password_validation_no_uppercase():
    with pytest.raises(HTTPException) as exc_info:
        auth_service.validate_password("abcd1234!")
    assert exc_info.value.status_code == 400
    assert "wielką literę" in exc_info.value.detail


def test_password_validation_no_lowercase():
    with pytest.raises(HTTPException) as exc_info:
        auth_service.validate_password("ABCD1234!")
    assert exc_info.value.status_code == 400
    assert "małą literę" in exc_info.value.detail


def test_password_validation_no_digit():
    with pytest.raises(HTTPException) as exc_info:
        auth_service.validate_password("AbcdEFGH!")
    assert exc_info.value.status_code == 400
    assert "cyfrę" in exc_info.value.detail


def test_password_validation_no_special_char():
    with pytest.raises(HTTPException) as exc_info:
        auth_service.validate_password("Abcd1234")
    assert exc_info.value.status_code == 400
    assert "znak specjalny" in exc_info.value.detail


def test_password_validation_valid():
    # Should not raise any exception
    auth_service.validate_password("StrongPass123!")


# ================== CURRENT USER ==================
@pytest.mark.asyncio
async def test_get_current_user_success(db_session: AsyncSession, user_data):
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    access_token = auth_service.create_token(subject=user.username, scope="access_token")
    
    current_user = await auth_service.get_current_user(token=access_token, db=db_session)
    assert current_user.username == user.username
    assert current_user.email == user.email


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(db_session: AsyncSession):
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.get_current_user(token="invalid_token", db=db_session)
    assert exc_info.value.status_code == 401
    assert "Nieprawidłowe dane uwierzytelniające" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_wrong_token_scope(db_session: AsyncSession, user_data):
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    # Create token with wrong scope
    wrong_scope_token = auth_service.create_token(subject=user.username, scope="refresh_token")
    
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.get_current_user(token=wrong_scope_token, db=db_session)
    assert exc_info.value.status_code == 401
    assert "Nieprawidłowy typ tokena" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_nonexistent_user(db_session: AsyncSession):
    # Create token for non-existent user
    token = auth_service.create_token(subject="nonexistent_user", scope="access_token")
    
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.get_current_user(token=token, db=db_session)
    assert exc_info.value.status_code == 401
    assert "Nieprawidłowe dane uwierzytelniające" in exc_info.value.detail


# ================== REFRESH ACCESS TOKEN ==================
@pytest.mark.asyncio
async def test_refresh_access_token_success(db_session: AsyncSession, user_data):
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    refresh_token = auth_service.create_token(subject=user.username, scope="refresh_token")
    user.refresh_token = refresh_token
    await db_session.commit()
    
    new_access_token = await auth_service.refresh_access_token(refresh_token, db_session)
    assert new_access_token is not None
    assert isinstance(new_access_token, str)


@pytest.mark.asyncio
async def test_refresh_access_token_invalid_token(db_session: AsyncSession):
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.refresh_access_token("invalid_token", db_session)
    assert exc_info.value.status_code == 401
    assert "Nieprawidłowe dane uwierzytelniające" in exc_info.value.detail


@pytest.mark.asyncio
async def test_refresh_access_token_wrong_scope(db_session: AsyncSession, user_data):
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    # Create token with wrong scope
    wrong_scope_token = auth_service.create_token(subject=user.username, scope="access_token")
    
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.refresh_access_token(wrong_scope_token, db_session)
    assert exc_info.value.status_code == 401
    assert "Nieprawidłowy typ tokena" in exc_info.value.detail


@pytest.mark.asyncio
async def test_refresh_access_token_nonexistent_user(db_session: AsyncSession):
    # Create token for non-existent user
    token = auth_service.create_token(subject="nonexistent_user", scope="refresh_token")
    
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.refresh_access_token(token, db_session)
    assert exc_info.value.status_code == 401
    assert "Nieprawidłowy refresh token" in exc_info.value.detail


# ================== EXPIRED TOKENS ==================
@pytest.mark.asyncio
async def test_expired_access_token(db_session: AsyncSession, user_data):
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    # Create token that expires immediately
    expired_token = auth_service.create_token(
        subject=user.username,
        scope="access_token",
        expires_delta=-1  # Token już wygasł
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.get_current_user(token=expired_token, db=db_session)
    assert exc_info.value.status_code == 401
    assert "Token wygasł" in exc_info.value.detail


@pytest.mark.asyncio
async def test_expired_refresh_token(db_session: AsyncSession, user_data):
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    # Create token that expires immediately
    expired_token = auth_service.create_token(
        subject=user.username,
        scope="refresh_token",
        expires_delta=-1  # Token już wygasł
    )
    user.refresh_token = expired_token
    await db_session.commit()
    
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.refresh_access_token(expired_token, db_session)
    assert exc_info.value.status_code == 401
    assert "Token wygasł" in exc_info.value.detail


@pytest.mark.asyncio
async def test_expired_email_confirmation_token(client: AsyncClient, db_session: AsyncSession, user_data):
    user = await create_user_db(user_data, db_session)
    # Create token that expires immediately
    expired_token = auth_service.create_token(
        subject=user.email,
        scope="email_confirm",
        expires_delta=-1  # Token już wygasł
    )
    
    response = await client.get(f"/api/auth/confirmed_email/{expired_token}")
    assert response.status_code == 400
    assert "Błąd weryfikacji" in response.json()["detail"]


@pytest.mark.asyncio
async def test_expired_password_reset_token(client: AsyncClient, db_session: AsyncSession, user_data):
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    # Create token that expires immediately
    expired_token = auth_service.create_token(
        subject=user.email,
        scope="reset_password",
        expires_delta=-1  # Token już wygasł
    )
    
    response = await client.post(
        "/api/auth/reset-password",
        json={"token": expired_token, "new_password": "NewStrongPass123!"}
    )
    assert response.status_code == 401
    assert "Nieprawidłowy token resetu hasła" in response.json()["detail"]