import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.auth import auth_service
from src.tests.conftest import (
    login_user_confirmed_true_and_hash_password,
    create_user_db
)


# ================== HELPER FUNCTIONS ==================
async def create_admin_user(user_data, db: AsyncSession):
    """Tworzy użytkownika z uprawnieniami administratora"""
    user = await login_user_confirmed_true_and_hash_password(user_data, db)
    user.is_admin = True
    await db.commit()
    await db.refresh(user)
    return user


async def create_regular_user(user_data, db: AsyncSession, username_suffix=""):
    """Tworzy zwykłego użytkownika"""
    user_data.username += username_suffix
    user_data.email = f"user{username_suffix}@example.com"
    return await create_user_db(user_data, db)


# ================== GET USERS TESTS ==================
@pytest.mark.asyncio
async def test_get_users_as_admin(client: AsyncClient, db_session: AsyncSession, user_data):
    # Utwórz admina i kilku użytkowników
    admin = await create_admin_user(user_data, db_session)
    for i in range(3):
        await create_regular_user(user_data, db_session, str(i))

    # Pobierz token dostępu dla admina
    access_token = auth_service.create_token(
        subject=admin.username,
        scope="access_token"
    )

    # Wykonaj zapytanie
    response = await client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    users = response.json()
    # Sprawdź liczbę użytkowników i obecność admina
    assert len(users) == 4  # admin + 3 użytkowników
    assert any(user["is_admin"] for user in users)


@pytest.mark.asyncio
async def test_get_users_as_regular_user(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz zwykłego użytkownika
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Próba dostępu do listy użytkowników
    response = await client.get(
        "/api/admin/users",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 403
    assert "Brak uprawnień administratora" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_users_with_pagination(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i wielu użytkowników
    admin = await create_admin_user(user_data, db_session)
    for i in range(15):
        await create_regular_user(user_data, db_session, str(i))

    access_token = auth_service.create_token(
        subject=admin.username,
        scope="access_token"
    )

    # Test pierwszej strony
    response = await client.get(
        "/api/admin/users?skip=0&limit=10",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    users_page1 = response.json()
    assert len(users_page1) == 10

    # Test drugiej strony
    response = await client.get(
        "/api/admin/users?skip=10&limit=10",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    users_page2 = response.json()
    # admin + 5 pozostałych użytkowników
    assert len(users_page2) == 6

    # Sprawdź czy nie ma duplikatów
    user_ids_page1 = {user["id"] for user in users_page1}
    user_ids_page2 = {user["id"] for user in users_page2}
    assert not user_ids_page1.intersection(user_ids_page2)


@pytest.mark.asyncio
async def test_get_users_limit_too_high(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina
    admin = await create_admin_user(user_data, db_session)
    access_token = auth_service.create_token(
        subject=admin.username,
        scope="access_token"
    )

    # Próba pobrania z limitem > 1000
    response = await client.get(
        "/api/admin/users?limit=1500",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    users = response.json()
    # tylko admin, bo nie utworzyliśmy innych użytkowników
    assert len(users) == 1


# ================== GET USER BY ID TESTS ==================
@pytest.mark.asyncio
async def test_get_user_by_id_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i użytkownika
    admin = await create_admin_user(user_data, db_session)
    user = await create_regular_user(user_data, db_session, "test")
    access_token = auth_service.create_token(
        subject=admin.username,
        scope="access_token"
    )

    # Pobierz użytkownika po ID
    response = await client.get(
        f"/api/admin/user/?user_id={user.id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    user_response = response.json()
    assert user_response["id"] == user.id
    assert user_response["username"] == user.username


@pytest.mark.asyncio
async def test_get_user_by_username_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i użytkownika
    admin = await create_admin_user(user_data, db_session)
    user = await create_regular_user(user_data, db_session, "test")
    access_token = auth_service.create_token(
        subject=admin.username,
        scope="access_token"
    )

    # Pobierz użytkownika po username
    response = await client.get(
        f"/api/admin/user/?username={user.username}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    user_response = response.json()
    assert user_response["username"] == user.username


@pytest.mark.asyncio
async def test_get_user_by_email_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i użytkownika
    admin = await create_admin_user(user_data, db_session)
    user = await create_regular_user(user_data, db_session, "test")
    access_token = auth_service.create_token(
        subject=admin.username,
        scope="access_token"
    )

    # Pobierz użytkownika po email
    response = await client.get(
        f"/api/admin/user/?email={user.email}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    user_response = response.json()
    assert user_response["email"] == user.email


@pytest.mark.asyncio
async def test_get_user_no_criteria(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina
    admin = await create_admin_user(user_data, db_session)
    access_token = auth_service.create_token(subject=admin.username, scope="access_token")

    # Próba pobrania bez kryteriów
    response = await client.get(
        "/api/admin/user/",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 400
    assert "Musisz podać przynajmniej jedno kryterium" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_nonexistent_user(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina
    admin = await create_admin_user(user_data, db_session)
    access_token = auth_service.create_token(subject=admin.username, scope="access_token")

    # Próba pobrania nieistniejącego użytkownika
    response = await client.get(
        "/api/admin/user/?user_id=999",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 404
    assert "Nie znaleziono użytkownika" in response.json()["detail"]


# ================== UPDATE USER PROFILE TESTS ==================
@pytest.mark.asyncio
async def test_update_user_profile_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i użytkownika
    admin = await create_admin_user(user_data, db_session)
    user = await create_regular_user(user_data, db_session, "test")
    access_token = auth_service.create_token(subject=admin.username, scope="access_token")

    # Aktualizuj profil użytkownika
    update_data = {
        "username": "new_username",
        "email": "new_email@example.com",
        "full_name": "New Name",
        "is_active": True
    }
    response = await client.patch(
        f"/api/admin/users/{user.id}/profile",
        headers={"Authorization": f"Bearer {access_token}"},
        json=update_data
    )
    assert response.status_code == 200
    updated_user = response.json()
    assert updated_user["username"] == update_data["username"]
    assert updated_user["email"] == update_data["email"]
    assert updated_user["full_name"] == update_data["full_name"]
    assert updated_user["is_active"] == update_data["is_active"]


@pytest.mark.asyncio
async def test_update_user_profile_duplicate_username(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i dwóch użytkowników
    admin = await create_admin_user(user_data, db_session)
    user1 = await create_regular_user(user_data, db_session, "1")
    user2 = await create_regular_user(user_data, db_session, "2")
    access_token = auth_service.create_token(subject=admin.username, scope="access_token")

    # Próba aktualizacji na istniejący username
    update_data = {
        "username": user2.username
    }
    response = await client.patch(
        f"/api/admin/users/{user1.id}/profile",
        headers={"Authorization": f"Bearer {access_token}"},
        json=update_data
    )
    assert response.status_code == 400
    assert "Nazwa użytkownika jest już zajęta" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_user_profile_duplicate_email(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i dwóch użytkowników
    admin = await create_admin_user(user_data, db_session)
    user1 = await create_regular_user(user_data, db_session, "1")
    user2 = await create_regular_user(user_data, db_session, "2")
    access_token = auth_service.create_token(subject=admin.username, scope="access_token")

    # Próba aktualizacji na istniejący email
    update_data = {
        "email": user2.email
    }
    response = await client.patch(
        f"/api/admin/users/{user1.id}/profile",
        headers={"Authorization": f"Bearer {access_token}"},
        json=update_data
    )
    assert response.status_code == 400
    assert "Adres e-mail jest już zajęty" in response.json()["detail"]


# ================== CONFIRM EMAIL TESTS ==================
@pytest.mark.asyncio
async def test_confirm_user_email_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i niepotwierdzony użytkownik
    admin = await create_admin_user(user_data, db_session)
    user = await create_regular_user(user_data, db_session, "test")
    access_token = auth_service.create_token(subject=admin.username, scope="access_token")

    # Potwierdź email użytkownika
    response = await client.patch(
        f"/api/admin/users/{user.id}/confirm-email",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    confirmed_user = response.json()
    assert confirmed_user["confirmed"] is True


@pytest.mark.asyncio
async def test_confirm_email_nonexistent_user(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina
    admin = await create_admin_user(user_data, db_session)
    access_token = auth_service.create_token(subject=admin.username, scope="access_token")

    # Próba potwierdzenia emaila nieistniejącego użytkownika
    response = await client.patch(
        "/api/admin/users/999/confirm-email",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 404
    assert "Nie znaleziono użytkownika" in response.json()["detail"]


# ================== REQUEST PASSWORD RESET TESTS ==================
@pytest.mark.asyncio
async def test_request_password_reset_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data,
    mock_email_service
):
    # Utwórz admina i użytkownika
    admin = await create_admin_user(user_data, db_session)
    user = await create_regular_user(user_data, db_session, "test")
    user.confirmed = True
    await db_session.commit()
    access_token = auth_service.create_token(subject=admin.username, scope="access_token")

    # Zleć reset hasła
    response = await client.post(
        f"/api/admin/users/{user.id}/request-password-reset",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "Wysłano e-mail do resetu hasła" in response.json()["detail"]
    assert mock_email_service.called


@pytest.mark.asyncio
async def test_request_password_reset_unconfirmed_email(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i użytkownika z niepotwierdzonym emailem
    admin = await create_admin_user(user_data, db_session)
    user = await create_regular_user(user_data, db_session, "test")
    access_token = auth_service.create_token(subject=admin.username, scope="access_token")

    # Próba zlecenia resetu hasła
    response = await client.post(
        f"/api/admin/users/{user.id}/request-password-reset",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 400
    assert "nie jest potwierdzony" in response.json()["detail"]


@pytest.mark.asyncio
async def test_request_password_reset_no_email(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i użytkownika bez emaila
    admin = await create_admin_user(user_data, db_session)
    user = await create_regular_user(user_data, db_session, "test")
    user.email = None
    await db_session.commit()
    access_token = auth_service.create_token(subject=admin.username, scope="access_token")

    # Próba zlecenia resetu hasła
    response = await client.post(
        f"/api/admin/users/{user.id}/request-password-reset",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 400
    assert "nie posiada adresu e-mail" in response.json()["detail"]


# ================== UPDATE ADMIN STATUS TESTS ==================
@pytest.mark.asyncio
async def test_grant_admin_status(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i zwykłego użytkownika
    admin = await create_admin_user(user_data, db_session)
    user = await create_regular_user(user_data, db_session, "test")
    access_token = auth_service.create_token(subject=admin.username, scope="access_token")

    # Nadaj uprawnienia admina
    response = await client.patch(
        f"/api/admin/users/{user.id}/admin-status",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"is_admin": True}
    )
    assert response.status_code == 200
    updated_user = response.json()
    assert updated_user["is_admin"] is True


@pytest.mark.asyncio
async def test_revoke_admin_status_last_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz jedynego admina
    admin = await create_admin_user(user_data, db_session)
    access_token = auth_service.create_token(subject=admin.username, scope="access_token")

    # Próba odebrania uprawnień ostatniemu adminowi
    response = await client.patch(
        f"/api/admin/users/{admin.id}/admin-status",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"is_admin": False}
    )
    assert response.status_code == 400
    assert "Nie można odebrać sobie uprawnień administratora" in response.json()["detail"]


@pytest.mark.asyncio
async def test_revoke_own_admin_status(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz dwóch adminów
    admin1 = await create_admin_user(user_data, db_session)
    admin2 = await create_regular_user(user_data, db_session, "admin2")
    admin2.is_admin = True
    await db_session.commit()
    access_token = auth_service.create_token(subject=admin1.username, scope="access_token")

    # Próba odebrania sobie uprawnień
    response = await client.patch(
        f"/api/admin/users/{admin1.id}/admin-status",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"is_admin": False}
    )
    assert response.status_code == 400
    assert "Nie można odebrać sobie uprawnień" in response.json()["detail"]


# ================== DELETE USER TESTS ==================
@pytest.mark.asyncio
async def test_delete_user_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i użytkownika
    admin = await create_admin_user(user_data, db_session)
    user = await create_regular_user(user_data, db_session, "test")
    access_token = auth_service.create_token(subject=admin.username, scope="access_token")

    # Usuń użytkownika
    response = await client.delete(
        f"/api/admin/users/{user.id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert "zostało usunięte" in response.json()["detail"]

    # Sprawdź czy użytkownik został usunięty
    response = await client.get(
        f"/api/admin/user/?user_id={user.id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_own_account_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina
    admin = await create_admin_user(user_data, db_session)
    access_token = auth_service.create_token(subject=admin.username, scope="access_token")

    # Próba usunięcia własnego konta
    response = await client.delete(
        f"/api/admin/users/{admin.id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 400
    assert "Nie można usunąć własnego konta" in response.json()["detail"]
