import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from src.services.auth import auth_service
from src.tests.conftest import login_user_confirmed_true_and_hash_password


# ================== HELPER FUNCTIONS ==================
async def create_conversation_history(
    user_id: int,
    db: AsyncSession,
    mode: str,
    messages: list
):
    """Tworzy historię konwersacji dla użytkownika"""
    from src.services.ai import save_conversation_message
    for msg in messages:
        await save_conversation_message(
            user_id=user_id,
            mode=mode,
            message=msg["text"],
            is_user_message=msg["is_user"],
            db=db
        )


# ================== EMPATHETIC MESSAGE TESTS ==================
@pytest.mark.asyncio
async def test_send_empathetic_message_success(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz użytkownika
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Mock odpowiedzi AI
    with patch("src.services.ai._call_ollama_chat_api") as mock_ai:
        mock_ai.return_value = "Rozumiem, że jest ci ciężko. Chcesz o tym porozmawiać?"
        
        # Wyślij wiadomość
        response = await client.post(
            "/api/echo/empathetic/send",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"text": "Czuję się smutny."}
        )
        assert response.status_code == 200
        data = response.json()
        assert "ai_response" in data
        assert isinstance(data["ai_response"], str)
        assert len(data["ai_response"]) > 0


@pytest.mark.asyncio
async def test_send_empathetic_message_empty(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    response = await client.post(
        "/api/echo/empathetic/send",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"text": "   "}
    )
    assert response.status_code == 400
    assert "nie może być pusta" in response.json()["detail"]


@pytest.mark.asyncio
async def test_send_empathetic_message_too_long(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    response = await client.post(
        "/api/echo/empathetic/send",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"text": "x" * 2001}
    )
    assert response.status_code == 422  # Validation error
    assert "String should have at most 2000 characters" in response.json()["detail"][0]["msg"]


# ================== PRACTICAL MESSAGE TESTS ==================
@pytest.mark.asyncio
async def test_send_practical_message_success(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Mock odpowiedzi AI
    with patch("src.services.ai._call_ollama_chat_api") as mock_ai:
        mock_ai.return_value = "1. Ustal priorytety\n2. Planuj zadania\n3. Eliminuj rozpraszacze"
        
        response = await client.post(
            "/api/echo/practical/send",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"text": "Jak mogę lepiej zarządzać czasem?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "ai_response" in data
        assert isinstance(data["ai_response"], str)
        assert len(data["ai_response"]) > 0


@pytest.mark.asyncio
async def test_send_practical_message_ai_error(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Symuluj błąd serwisu AI
    with patch("src.services.ai._call_ollama_chat_api", side_effect=Exception("AI service error")):
        response = await client.post(
            "/api/echo/practical/send",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"text": "Test message"}
        )
        assert response.status_code == 500
        assert "Wystąpił nieoczekiwany błąd: AI service error" in response.json()["detail"]


# ================== DIARY TESTS ==================
@pytest.mark.asyncio
async def test_send_diary_message_success(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    response = await client.post(
        "/api/echo/diary/send",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"text": "Dzisiejszy dzień był bardzo produktywny."}
    )
    assert response.status_code == 200
    data = response.json()
    assert "entry" in data
    assert "id" in data["entry"]
    assert "content" in data["entry"]
    assert "created_at" in data["entry"]


@pytest.mark.asyncio
async def test_send_diary_message_too_long(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    response = await client.post(
        "/api/echo/diary/send",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"text": "x" * 5001}
    )
    assert response.status_code == 422  # Validation error
    assert "String should have at most 2000 characters" in response.json()["detail"][0]["msg"]


# ================== HISTORY TESTS ==================
@pytest.mark.asyncio
async def test_get_empathetic_history(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Utwórz historię konwersacji
    messages = [
        {"text": "Czuję się smutny", "is_user": True},
        {"text": "Rozumiem, że jest ci ciężko", "is_user": False},
        {"text": "Tak, bardzo", "is_user": True}
    ]
    await create_conversation_history(
        user.id,
        db_session,
        "empathetic",
        messages
    )

    # Pobierz historię
    response = await client.get(
        "/api/echo/empathetic/history",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert "count" in data
    assert data["count"] == 3
    assert len(data["history"]) == 3


@pytest.mark.asyncio
async def test_get_practical_history(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Utwórz historię konwersacji
    messages = [
        {"text": "Jak lepiej się uczyć?", "is_user": True},
        {"text": "Oto kilka wskazówek...", "is_user": False}
    ]
    await create_conversation_history(
        user.id,
        db_session,
        "practical",
        messages
    )

    # Pobierz historię
    response = await client.get(
        "/api/echo/practical/history",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert "count" in data
    assert data["count"] == 2
    assert len(data["history"]) == 2


@pytest.mark.asyncio
async def test_get_diary_history(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Utwórz wpisy w dzienniku
    messages = [
        {"text": "Pierwszy wpis", "is_user": True},
        {"text": "Drugi wpis", "is_user": True}
    ]
    await create_conversation_history(
        user.id,
        db_session,
        "diary",
        messages
    )

    # Pobierz historię
    response = await client.get(
        "/api/echo/diary/history",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert "count" in data
    assert data["count"] == 2
    assert len(data["history"]) == 2


@pytest.mark.asyncio
async def test_history_limit_validation(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Test limitu > 1000
    response = await client.get(
        "/api/echo/empathetic/history?limit=1500",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "history" in data

    # Test limitu < 1
    response = await client.get(
        "/api/echo/empathetic/history?limit=0",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "history" in data


# ================== DIAGNOSTICS TESTS ==================
@pytest.mark.asyncio
async def test_get_ai_diagnostics(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Test diagnostyki
    response = await client.get(
        "/api/echo/diagnostics",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "ollama_url" in data
    assert "model" in data


# ================== STATS TESTS ==================
@pytest.mark.asyncio
async def test_get_user_stats(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Utwórz różne typy wiadomości
    await create_conversation_history(
        user.id,
        db_session,
        "empathetic",
        [{"text": "Test empathetic", "is_user": True}]
    )
    await create_conversation_history(
        user.id,
        db_session,
        "practical",
        [{"text": "Test practical", "is_user": True}]
    )
    await create_conversation_history(
        user.id,
        db_session,
        "diary",
        [{"text": "Test diary", "is_user": True}]
    )

    # Pobierz statystyki
    response = await client.get(
        "/api/echo/stats",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["empathetic_messages"] == 1
    assert data["practical_messages"] == 1
    assert data["diary_entries"] == 1
    assert data["total_messages"] == 3
