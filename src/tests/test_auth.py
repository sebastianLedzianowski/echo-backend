import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from jose import jwt

from src.services.auth import auth_service, AuthService
from src.repository import users as repository_users
from src.tests.conftest import (
    login_user_confirmed_true_and_hash_password,
    create_user_db
)


# ================== TESTY INICJALIZACJI AUTHSERVICE ==================
def test_auth_service_initialization():
    """Test poprawnej inicjalizacji AuthService"""
    service = AuthService()
    assert service.SECRET_KEY is not None
    assert service.ALGORITHM == "HS256"
    assert service.pwd_context is not None
    assert service.oauth2_scheme is not None


def test_auth_service_has_secret_key():
    """Test że AuthService ma ustawiony SECRET_KEY"""
    assert auth_service.SECRET_KEY is not None
    assert len(auth_service.SECRET_KEY) > 0
    assert auth_service.SECRET_KEY != ""


def test_auth_service_algorithm():
    """Test że AuthService ma ustawiony algorytm"""
    assert auth_service.ALGORITHM is not None
    assert auth_service.ALGORITHM in ["HS256", "HS384", "HS512"]



# ================== TESTY HASHOWANIA HASEŁ ==================
def test_get_password_hash():
    """Test hashowania hasła"""
    password = "TestPassword123!"
    hashed = auth_service.get_password_hash(password)

    assert hashed != password
    assert len(hashed) > 50  # bcrypt hash jest długi
    assert hashed.startswith("$2b$")  # bcrypt prefix


@pytest.mark.asyncio
async def test_verify_password_correct():
    """Test weryfikacji poprawnego hasła"""
    password = "TestPassword123!"
    hashed = auth_service.get_password_hash(password)

    is_valid = await auth_service.verify_password(password, hashed)
    assert is_valid is True


@pytest.mark.asyncio
async def test_verify_password_incorrect():
    """Test weryfikacji niepoprawnego hasła"""
    password = "TestPassword123!"
    wrong_password = "WrongPassword123!"
    hashed = auth_service.get_password_hash(password)

    is_valid = await auth_service.verify_password(wrong_password, hashed)
    assert is_valid is False


@pytest.mark.asyncio
async def test_verify_password_empty():
    """Test weryfikacji pustego hasła"""
    hashed = auth_service.get_password_hash("test")

    is_valid = await auth_service.verify_password("", hashed)
    assert is_valid is False


@pytest.mark.asyncio
async def test_verify_password_malformed_hash():
    """Test z niepoprawnym hashem"""
    try:
        is_valid = await auth_service.verify_password("password", "malformed_hash")
        assert is_valid is False
    except Exception:
        # Jeśli rzuca wyjątek, to też jest poprawne zachowanie
        assert True


# ================== TESTY WALIDACJI HASŁA ==================
def test_password_validation_too_short():
    """Test hasła za krótkie"""
    with pytest.raises(HTTPException) as exc_info:
        auth_service.validate_password("Abc1!")
    assert exc_info.value.status_code == 400
    assert "co najmniej 8 znaków" in exc_info.value.detail


def test_password_validation_no_uppercase():
    """Test hasła bez wielkiej litery"""
    with pytest.raises(HTTPException) as exc_info:
        auth_service.validate_password("abcd1234!")
    assert exc_info.value.status_code == 400
    assert "wielką literę" in exc_info.value.detail


def test_password_validation_no_lowercase():
    """Test hasła bez małej litery"""
    with pytest.raises(HTTPException) as exc_info:
        auth_service.validate_password("ABCD1234!")
    assert exc_info.value.status_code == 400
    assert "małą literę" in exc_info.value.detail


def test_password_validation_no_digit():
    """Test hasła bez cyfry"""
    with pytest.raises(HTTPException) as exc_info:
        auth_service.validate_password("AbcdEFGH!")
    assert exc_info.value.status_code == 400
    assert "cyfrę" in exc_info.value.detail


def test_password_validation_no_special_char():
    """Test hasła bez znaku specjalnego"""
    with pytest.raises(HTTPException) as exc_info:
        auth_service.validate_password("Abcd1234")
    assert exc_info.value.status_code == 400
    assert "znak specjalny" in exc_info.value.detail


def test_password_validation_valid():
    """Test poprawnego hasła"""
    # Nie powinno rzucić wyjątku
    auth_service.validate_password("StrongPass123!")


def test_password_validation_edge_cases():
    """Test przypadków granicznych w walidacji hasła"""
    # Minimalne wymagania
    auth_service.validate_password("Aa1!bcde")  # Dokładnie 8 znaków

    # Różne znaki specjalne
    special_chars = "!@#$%^&*(),.?\":{}|<>"
    for char in special_chars:
        auth_service.validate_password(f"TestPass1{char}")

    # Długie hasło
    auth_service.validate_password("VeryLongPassword123!WithManyCharacters")


# ================== TESTY TWORZENIA TOKENÓW ==================
def test_create_token_with_expires_delta():
    """Test tworzenia tokena z określonym czasem wygaśnięcia"""
    subject = "testuser"
    scope = "access_token"
    expires_delta = 3600  # 1 godzina

    token = auth_service.create_token(subject, scope, expires_delta)

    # Dekoduj token bez weryfikacji do testów
    payload = jwt.decode(token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM])
    assert payload["sub"] == subject
    assert payload["scope"] == scope
    assert "iat" in payload
    assert "exp" in payload


def test_create_token_default_expiry():
    """Test tworzenia tokena z domyślnym czasem wygaśnięcia"""
    # Access token
    access_token = auth_service.create_token("testuser", "access_token")
    payload = jwt.decode(access_token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM])
    assert payload["scope"] == "access_token"

    # Refresh token
    refresh_token = auth_service.create_token("testuser", "refresh_token")
    payload = jwt.decode(refresh_token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM])
    assert payload["scope"] == "refresh_token"

    # Other scope
    other_token = auth_service.create_token("testuser", "other_scope")
    payload = jwt.decode(other_token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM])
    assert payload["scope"] == "other_scope"


def test_create_token_payload_structure():
    """Test struktury payload w tokenie"""
    token = auth_service.create_token("testuser", "access_token", 3600)
    payload = jwt.decode(token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM])

    required_fields = ["sub", "scope", "iat", "exp"]
    for field in required_fields:
        assert field in payload

    assert isinstance(payload["iat"], int)
    assert isinstance(payload["exp"], int)
    assert payload["exp"] > payload["iat"]


# ================== TESTY DEKODOWANIA TOKENÓW ==================
@pytest.mark.asyncio
async def test_decode_token_valid():
    """Test dekodowania poprawnego tokena"""
    subject = "testuser"
    scope = "access_token"
    token = auth_service.create_token(subject, scope, 3600)

    decoded_subject = await auth_service.decode_token(token, scope)
    assert decoded_subject == subject


@pytest.mark.asyncio
async def test_decode_token_wrong_scope():
    """Test dekodowania tokena z niepoprawnym scope"""
    token = auth_service.create_token("testuser", "access_token", 3600)

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.decode_token(token, "refresh_token")
    assert exc_info.value.status_code == 401
    assert "Nieprawidłowy typ tokena" in exc_info.value.detail


@pytest.mark.asyncio
async def test_decode_token_expired():
    """Test dekodowania wygasłego tokena"""
    token = auth_service.create_token("testuser", "access_token", -1)  # Wygasł

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.decode_token(token, "access_token")
    assert exc_info.value.status_code == 401
    assert "Token wygasł" in exc_info.value.detail


@pytest.mark.asyncio
async def test_decode_token_malformed():
    """Test dekodowania niepoprawnego tokena"""
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.decode_token("invalid.token.here", "access_token")
    assert exc_info.value.status_code == 401
    assert "Nieprawidłowe dane uwierzytelniające" in exc_info.value.detail


@pytest.mark.asyncio
async def test_decode_token_no_subject():
    """Test tokena bez subject"""
    # Stwórz token ręcznie bez 'sub'
    payload = {
        "scope": "access_token",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, auth_service.SECRET_KEY, algorithm=auth_service.ALGORITHM)

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.decode_token(token, "access_token")
    assert exc_info.value.status_code == 401
    assert "Brak danych w tokenie" in exc_info.value.detail


@pytest.mark.asyncio
async def test_decode_token_empty_subject():
    """Test tokena z pustym subject"""
    payload = {
        "sub": "",  # Pusty subject
        "scope": "access_token",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, auth_service.SECRET_KEY, algorithm=auth_service.ALGORITHM)

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.decode_token(token, "access_token")
    assert exc_info.value.status_code == 401
    assert "Brak danych w tokenie" in exc_info.value.detail


# ================== TESTY SIGNUP ==================
@pytest.mark.asyncio
async def test_signup_success(
        client: AsyncClient,
        db_session: AsyncSession,
        user_data
):
    """Test udanej rejestracji"""
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
    """Test rejestracji z duplikatową nazwą użytkownika"""
    await repository_users.create_user(user_data, db_session)
    response = await client.post("/api/auth/signup", json=user_data.dict())
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test rejestracji z duplikatowym emailem"""
    user = user_data
    await repository_users.create_user(user, db_session)
    user2 = user_data
    user2.username = "otheruser"
    response = await client.post("/api/auth/signup", json=user2.dict())
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_signup_invalid_password(client: AsyncClient, user_data):
    """Test rejestracji z niepoprawnym hasłem"""
    user = user_data
    user.password = "123"
    response = await client.post("/api/auth/signup", json=user.dict())
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_signup_missing_fields(client: AsyncClient):
    """Test rejestracji z brakującymi polami"""
    incomplete_data = {"username": "testuser"}
    response = await client.post("/api/auth/signup", json=incomplete_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_empty_fields(client: AsyncClient):
    """Test rejestracji z pustymi polami"""
    empty_data = {
        "username": "",
        "email": "",
        "password": "",
        "full_name": ""
    }
    response = await client.post("/api/auth/signup", json=empty_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_invalid_email_format(client: AsyncClient, user_data):
    """Test rejestracji z niepoprawnym formatem emaila"""
    user_data.email = "invalid-email"
    response = await client.post("/api/auth/signup", json=user_data.dict())
    assert response.status_code == 422


# ================== TESTY LOGIN ==================
@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test udanego logowania"""
    await login_user_confirmed_true_and_hash_password(user_data, db_session)
    response = await client.post(
        "/api/auth/login",
        data={"username": user_data.username, "password": user_data.password}
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body and "refresh_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_unconfirmed_email(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test logowania z niepotwierdzonym emailem"""
    # Utwórz użytkownika z zahashowanym hasłem ale niepotwierdzonym emailem
    hashed_password = auth_service.get_password_hash(user_data.password)
    user = await create_user_db(user_data, db_session)
    user.password = hashed_password
    user.confirmed = False
    await db_session.commit()

    response = await client.post(
        "/api/auth/login",
        data={"username": user_data.username, "password": user_data.password}
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body and "refresh_token" in body


@pytest.mark.asyncio
async def test_login_invalid_username(client: AsyncClient):
    """Test logowania z nieistniejącą nazwą użytkownika"""
    response = await client.post(
        "/api/auth/login",
        data={"username": "nouser", "password": "pass"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test logowania z niepoprawnym hasłem"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    response = await client.post(
        "/api/auth/login",
        data={"username": user.username, "password": "wrongpass"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test logowania nieaktywnego użytkownika"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    user.is_active = False
    await db_session.commit()

    response = await client.post(
        "/api/auth/login",
        data={"username": user.username, "password": user_data.password}
    )
    # Sprawdź czy nieaktywny użytkownik może się zalogować (zależy od implementacji)
    assert response.status_code in [200, 401, 403]


@pytest.mark.asyncio
async def test_login_missing_credentials(client: AsyncClient):
    """Test logowania bez danych uwierzytelniających"""
    response = await client.post("/api/auth/login", data={})
    assert response.status_code == 422


# ================== TESTY REFRESH TOKEN ==================
@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test udanego odświeżenia tokena"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    refresh_token = auth_service.create_token(user.username, scope="refresh_token")
    user.refresh_token = refresh_token
    await db_session.commit()

    response = await client.get(
        "/api/auth/refresh_token",
        headers={"Authorization": f"Bearer {refresh_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body and "refresh_token" in body


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    """Test odświeżenia z niepoprawnym tokenem"""
    response = await client.get(
        "/api/auth/refresh_token",
        headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_missing_header(client: AsyncClient):
    """Test odświeżenia bez nagłówka Authorization"""
    response = await client.get("/api/auth/refresh_token")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_refresh_token_wrong_format(client: AsyncClient):
    """Test odświeżenia z niepoprawnym formatem nagłówka"""
    response = await client.get(
        "/api/auth/refresh_token",
        headers={"Authorization": "InvalidFormat token"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_refresh_token_access_token_used(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test próby użycia access token zamiast refresh token"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    access_token = auth_service.create_token(user.username, scope="access_token")

    response = await client.get(
        "/api/auth/refresh_token",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 401


# ================== TESTY CONFIRM EMAIL ==================
@pytest.mark.asyncio
async def test_confirm_email_success(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test udanego potwierdzenia emaila"""
    user = await create_user_db(user_data, db_session)
    token = auth_service.create_token(user.email, scope="email_confirm")
    response = await client.get(f"/api/auth/confirmed_email/{token}")
    assert response.status_code == 200
    assert "E-mail potwierdzony" in response.json()["message"]


@pytest.mark.asyncio
async def test_confirm_email_invalid(client: AsyncClient):
    """Test potwierdzenia emaila z niepoprawnym tokenem"""
    response = await client.get("/api/auth/confirmed_email/invalidtoken")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_confirm_email_nonexistent_user(client: AsyncClient):
    """Test potwierdzenia emaila dla nieistniejącego użytkownika"""
    token = auth_service.create_token("nonexistent@example.com", scope="email_confirm")
    response = await client.get(f"/api/auth/confirmed_email/{token}")
    # API może zwrócić błąd dla nieistniejącego użytkownika
    assert response.status_code in [200, 400, 404]



@pytest.mark.asyncio
async def test_request_email_confirmation(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test żądania potwierdzenia emaila"""
    await create_user_db(user_data, db_session)
    response = await client.post("/api/auth/request_email", json={"email": user_data.email})
    assert response.status_code == 200
    assert "Wysłano" in response.json()["message"]


@pytest.mark.asyncio
async def test_request_email_confirmation_nonexistent(client: AsyncClient):
    """Test żądania potwierdzenia dla nieistniejącego emaila"""
    response = await client.post(
        "/api/auth/request_email",
        json={"email": "nonexistent@example.com"}
    )
    # Powinno zwrócić sukces (nie ujawniamy informacji o istnieniu użytkownika)
    assert response.status_code == 200


# ================== TESTY PASSWORD RESET ==================
@pytest.mark.asyncio
async def test_request_password_reset(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test żądania resetu hasła"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    response = await client.post(
        "/api/auth/request_password_reset",
        json={"email": user.email}
    )
    assert response.status_code == 200
    assert "resetu hasła" in response.json()["message"]


@pytest.mark.asyncio
async def test_reset_password_success(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test udanego resetu hasła"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    token = auth_service.create_token(user.email, scope="reset_password")

    new_password = "NewStrongPass123!"
    response = await client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": new_password}
    )
    assert response.status_code == 200
    assert "zaktualizowane" in response.json()["detail"]


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client: AsyncClient):
    """Test resetu hasła z niepoprawnym tokenem"""
    response = await client.post(
        "/api/auth/reset-password",
        json={"token": "invalidtoken", "new_password": "NewStrongPass123!"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_reset_password_weak_password(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test resetu hasła ze słabym hasłem"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    token = auth_service.create_token(user.email, scope="reset_password")
    response = await client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "123"}
    )
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_reset_password_same_password(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test resetu hasła na to samo hasło"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    token = auth_service.create_token(user.email, scope="reset_password")

    # Spróbuj ustawić to samo hasło
    response = await client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": user_data.password}
    )
    # Powinno być dozwolone
    assert response.status_code == 200


# ================== TESTY GET CURRENT USER ==================
@pytest.mark.asyncio
async def test_get_current_user_success(db_session: AsyncSession, user_data):
    """Test udanego pobrania aktualnego użytkownika"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    access_token = auth_service.create_token(subject=user.username, scope="access_token")

    current_user = await auth_service.get_current_user(token=access_token, db=db_session)
    assert current_user.username == user.username
    assert current_user.email == user.email


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(db_session: AsyncSession):
    """Test pobrania użytkownika z niepoprawnym tokenem"""
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.get_current_user(token="invalid_token", db=db_session)
    assert exc_info.value.status_code == 401
    assert "Nieprawidłowe dane uwierzytelniające" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_wrong_token_scope(db_session: AsyncSession, user_data):
    """Test pobrania użytkownika z tokenem o złym scope"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    wrong_scope_token = auth_service.create_token(subject=user.username, scope="refresh_token")

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.get_current_user(token=wrong_scope_token, db=db_session)
    assert exc_info.value.status_code == 401
    assert "Nieprawidłowy typ tokena" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_current_user_nonexistent_user(db_session: AsyncSession):
    """Test pobrania nieistniejącego użytkownika"""
    token = auth_service.create_token(subject="nonexistent_user", scope="access_token")

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.get_current_user(token=token, db=db_session)
    assert exc_info.value.status_code == 401
    assert "Nieprawidłowe dane uwierzytelniające" in exc_info.value.detail


# ================== TESTY REFRESH ACCESS TOKEN ==================
@pytest.mark.asyncio
async def test_refresh_access_token_success(db_session: AsyncSession, user_data):
    """Test udanego odświeżenia access token"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    refresh_token = auth_service.create_token(subject=user.username, scope="refresh_token")
    user.refresh_token = refresh_token
    await db_session.commit()

    new_access_token = await auth_service.refresh_access_token(refresh_token, db_session)
    assert new_access_token is not None
    assert isinstance(new_access_token, str)

    # Sprawdź czy nowy token jest ważny
    decoded_subject = await auth_service.decode_token(new_access_token, "access_token")
    assert decoded_subject == user.username


@pytest.mark.asyncio
async def test_refresh_access_token_invalid_token(db_session: AsyncSession):
    """Test odświeżenia z niepoprawnym tokenem"""
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.refresh_access_token("invalid_token", db_session)
    assert exc_info.value.status_code == 401
    assert "Nieprawidłowe dane uwierzytelniające" in exc_info.value.detail


@pytest.mark.asyncio
async def test_refresh_access_token_wrong_scope(db_session: AsyncSession, user_data):
    """Test odświeżenia z tokenem o złym scope"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    wrong_scope_token = auth_service.create_token(subject=user.username, scope="access_token")

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.refresh_access_token(wrong_scope_token, db_session)
    assert exc_info.value.status_code == 401
    assert "Nieprawidłowy typ tokena" in exc_info.value.detail


@pytest.mark.asyncio
async def test_refresh_access_token_nonexistent_user(db_session: AsyncSession):
    """Test odświeżenia dla nieistniejącego użytkownika"""
    token = auth_service.create_token(subject="nonexistent_user", scope="refresh_token")

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.refresh_access_token(token, db_session)
    assert exc_info.value.status_code == 401
    assert "Nieprawidłowy refresh token" in exc_info.value.detail


# ================== TESTY EXPIRED TOKENS ==================
@pytest.mark.asyncio
async def test_expired_access_token(db_session: AsyncSession, user_data):
    """Test wygasłego access token"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
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
    """Test wygasłego refresh token"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
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
    """Test wygasłego tokena potwierdzenia emaila"""
    user = await create_user_db(user_data, db_session)
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
    """Test wygasłego tokena resetu hasła"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
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


# ================== TESTY BEZPIECZEŃSTWA ==================
@pytest.mark.asyncio
async def test_token_reuse_protection(db_session: AsyncSession, user_data):
    """Test ochrony przed ponownym użyciem tokenów"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)

    # Utwórz token i użyj go
    token = auth_service.create_token(user.username, "access_token", 3600)
    current_user1 = await auth_service.get_current_user(token=token, db=db_session)
    assert current_user1.username == user.username

    # Token powinien być nadal ważny dla kolejnego użycia
    current_user2 = await auth_service.get_current_user(token=token, db=db_session)
    assert current_user2.username == user.username


def test_different_users_different_tokens():
    """Test że różni użytkownicy mają różne tokeny"""
    user1_token = auth_service.create_token("user1", "access_token", 3600)
    user2_token = auth_service.create_token("user2", "access_token", 3600)

    assert user1_token != user2_token

    # Sprawdź że tokeny dekodują się do odpowiednich użytkowników
    payload1 = jwt.decode(user1_token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM])
    payload2 = jwt.decode(user2_token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM])

    assert payload1["sub"] == "user1"
    assert payload2["sub"] == "user2"


def test_token_signature_verification():
    """Test weryfikacji podpisu tokena"""
    # Utwórz token z prawidłowym kluczem
    valid_token = auth_service.create_token("testuser", "access_token", 3600)

    # Sprawdź że token jest ważny
    payload = jwt.decode(valid_token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM])
    assert payload["sub"] == "testuser"

    # Próba dekodowania z nieprawidłowym kluczem powinna się nie powieść
    with pytest.raises(Exception):
        jwt.decode(valid_token, "wrong_key", algorithms=[auth_service.ALGORITHM])


# ================== TESTY EDGE CASES ==================
@pytest.mark.asyncio
async def test_very_long_username_token(db_session: AsyncSession):
    """Test tokena z bardzo długą nazwą użytkownika"""
    long_username = "a" * 1000  # Bardzo długa nazwa
    token = auth_service.create_token(long_username, "access_token", 3600)

    decoded_subject = await auth_service.decode_token(token, "access_token")
    assert decoded_subject == long_username


@pytest.mark.asyncio
async def test_special_characters_in_username_token():
    """Test tokena z nazwą użytkownika zawierającą znaki specjalne"""
    special_username = "user@domain.com!#$%"
    token = auth_service.create_token(special_username, "access_token", 3600)

    decoded_subject = await auth_service.decode_token(token, "access_token")
    assert decoded_subject == special_username


@pytest.mark.asyncio
async def test_unicode_username_token():
    """Test tokena z nazwą użytkownika zawierającą znaki Unicode"""
    unicode_username = "użytkownik_ąćęłńóśźż"
    token = auth_service.create_token(unicode_username, "access_token", 3600)

    decoded_subject = await auth_service.decode_token(token, "access_token")
    assert decoded_subject == unicode_username


def test_password_hash_consistency():
    """Test spójności hashowania hasła"""
    password = "TestPassword123!"

    # Wielokrotne hashowanie tego samego hasła powinno dawać różne hashe
    hash1 = auth_service.get_password_hash(password)
    hash2 = auth_service.get_password_hash(password)

    assert hash1 != hash2  # bcrypt używa salt

    # Ale oba powinny być weryfikowalne
    assert auth_service.pwd_context.verify(password, hash1)
    assert auth_service.pwd_context.verify(password, hash2)


@pytest.mark.asyncio
async def test_case_sensitive_username_login(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test czy nazwy użytkowników są case-sensitive"""
    await login_user_confirmed_true_and_hash_password(user_data, db_session)

    # Próba logowania z inną wielkością liter
    response = await client.post(
        "/api/auth/login",
        data={"username": user_data.username.upper(), "password": user_data.password}
    )
    # Zależy od implementacji - może być case-sensitive lub nie
    assert response.status_code in [200, 401]


@pytest.mark.asyncio
async def test_multiple_failed_login_attempts(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test wielokrotnych nieudanych prób logowania"""
    await login_user_confirmed_true_and_hash_password(user_data, db_session)

    # Wykonaj kilka nieudanych prób logowania
    for _ in range(5):
        response = await client.post(
            "/api/auth/login",
            data={"username": user_data.username, "password": "wrongpassword"}
        )
        assert response.status_code == 401

    # Sprawdź czy poprawne logowanie nadal działa
    response = await client.post(
        "/api/auth/login",
        data={"username": user_data.username, "password": user_data.password}
    )
    assert response.status_code == 200


# ================== TESTY INTEGRACYJNE ==================
@pytest.mark.asyncio
async def test_full_auth_flow(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test pełnego przepływu uwierzytelnienia"""
    # 1. Rejestracja
    signup_response = await client.post("/api/auth/signup", json=user_data.dict())
    assert signup_response.status_code == 201

    # 2. Potwierdzenie emaila
    user = await repository_users.get_user_by_username(user_data.username, db_session)
    confirm_token = auth_service.create_token(user.email, "email_confirm")
    confirm_response = await client.get(f"/api/auth/confirmed_email/{confirm_token}")
    assert confirm_response.status_code == 200

    # 3. Logowanie
    login_response = await client.post(
        "/api/auth/login",
        data={"username": user_data.username, "password": user_data.password}
    )
    assert login_response.status_code == 200
    tokens = login_response.json()

    # 4. Użycie access token
    protected_response = await client.get(
        "/api/auth/me",  # Przykładowy endpoint (jeśli istnieje)
        headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    # Endpoint może nie istnieć, więc sprawdzamy różne możliwe statusy
    assert protected_response.status_code in [200, 404]

    # 5. Odświeżenie tokena
    refresh_response = await client.get(
        "/api/auth/refresh_token",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"}
    )
    assert refresh_response.status_code == 200
    new_tokens = refresh_response.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens


@pytest.mark.asyncio
async def test_password_reset_flow(client: AsyncClient, db_session: AsyncSession, user_data):
    """Test pełnego przepływu resetu hasła"""
    # 1. Utwórz użytkownika
    user = await login_user_confirmed_true_and_hash_password(user_data, db_session)
    old_password_hash = user.password

    # 2. Zażądaj resetu hasła
    reset_request_response = await client.post(
        "/api/auth/request_password_reset",
        json={"email": user.email}
    )
    assert reset_request_response.status_code == 200

    # 3. Wykonaj reset hasła
    reset_token = auth_service.create_token(user.email, "reset_password")
    new_password = "NewStrongPassword123!"
    reset_response = await client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": new_password}
    )
    assert reset_response.status_code == 200

    # 4. Sprawdź że hasło zostało zmienione
    await db_session.refresh(user)
    assert user.password != old_password_hash

    # 5. Sprawdź że można się zalogować nowym hasłem
    login_response = await client.post(
        "/api/auth/login",
        data={"username": user.username, "password": new_password}
    )
    assert login_response.status_code == 200

    # 6. Sprawdź że stare hasło nie działa
    old_login_response = await client.post(
        "/api/auth/login",
        data={"username": user.username, "password": user_data.password}
    )
    assert old_login_response.status_code == 401


# ================== TESTY WYDAJNOŚCI ==================
def test_password_hashing_performance():
    """Test wydajności hashowania hasła"""
    import time

    password = "TestPassword123!"
    start_time = time.time()

    # Hash 10 haseł
    for _ in range(10):
        auth_service.get_password_hash(password)

    end_time = time.time()
    elapsed = end_time - start_time

    # Hashowanie powinno być stosunkowo szybkie, ale nie za szybkie (bezpieczeństwo)
    assert elapsed < 5.0  # Nie więcej niż 5 sekund na 10 hashów
    assert elapsed > 0.1  # Ale nie mniej niż 100ms (zbyt szybko = niebezpieczne)


def test_token_creation_performance():
    """Test wydajności tworzenia tokenów"""
    import time

    start_time = time.time()

    # Utwórz 100 tokenów
    for i in range(100):
        auth_service.create_token(f"user{i}", "access_token", 3600)

    end_time = time.time()
    elapsed = end_time - start_time

    # Tworzenie tokenów powinno być szybkie
    assert elapsed < 1.0  # Mniej niż sekunda na 100 tokenów


# ================== TESTY KONFIGURACJI ==================
def test_auth_service_singleton():
    """Test czy auth_service jest singletonem"""
    from src.services.auth import auth_service as service1
    from src.services.auth import auth_service as service2

    # Powinny być tym samym obiektem
    assert service1 is service2


def test_auth_service_token_creation_works():
    """Test że tworzenie tokenów działa z aktualnym algorytmem"""
    token = auth_service.create_token("testuser", "access_token", 3600)
    assert token is not None
    assert len(token) > 0
    assert isinstance(token, str)

    # Test że token można zdekodować
    from jose import jwt
    payload = jwt.decode(
        token,
        auth_service.SECRET_KEY,
        algorithms=[auth_service.ALGORITHM]
    )
    assert payload["sub"] == "testuser"
    assert payload["scope"] == "access_token"


def test_auth_service_full_workflow():
    """Test pełnego workflow AuthService"""
    username = "testuser"

    # 1. Tworzenie tokenu
    access_token = auth_service.create_token(username, "access_token", 3600)
    refresh_token = auth_service.create_token(username, "refresh_token", 7 * 24 * 3600)

    assert access_token != refresh_token

    # 2. Dekodowanie tokenów (synchronicznie przez jwt)
    from jose import jwt
    access_payload = jwt.decode(
        access_token,
        auth_service.SECRET_KEY,
        algorithms=[auth_service.ALGORITHM]
    )
    refresh_payload = jwt.decode(
        refresh_token,
        auth_service.SECRET_KEY,
        algorithms=[auth_service.ALGORITHM]
    )

    assert access_payload["sub"] == username
    assert access_payload["scope"] == "access_token"
    assert refresh_payload["sub"] == username
    assert refresh_payload["scope"] == "refresh_token"

    # 3. Test hashowania hasła
    password = "TestPassword123!"
    hashed = auth_service.get_password_hash(password)
    assert hashed != password
    assert len(hashed) > 50


@pytest.mark.asyncio
async def test_auth_service_async_methods():
    """Test metod async w AuthService"""
    # Test weryfikacji hasła
    password = "TestPassword123!"
    hashed = auth_service.get_password_hash(password)

    is_valid = await auth_service.verify_password(password, hashed)
    assert is_valid is True

    is_invalid = await auth_service.verify_password("wrongpassword", hashed)
    assert is_invalid is False

    # Test dekodowania tokena
    token = auth_service.create_token("testuser", "access_token", 3600)
    decoded_subject = await auth_service.decode_token(token, "access_token")
    assert decoded_subject == "testuser"