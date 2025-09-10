import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from src.services.auth import auth_service
from src.database.models import DiaryEntry, ConversationHistory, ApiHit, SystemMetrics, PsychologicalTest, LLMMetrics
from src.tests.conftest import login_user_confirmed_true_and_hash_password
from src.tests.test_admin import create_admin_user, create_regular_user


# ================== HELPER FUNCTIONS ==================
async def create_diary_entry(
    user_id: int,
    db: AsyncSession,
    days_ago: int = 0
):
    """Tworzy wpis w dzienniku"""
    entry = DiaryEntry(
        user_id=user_id,
        title="Test Entry",
        content="Test Content",
        emotion_tags="happy,excited",
        created_at=datetime.utcnow() - timedelta(days=days_ago)
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def create_conversation(
    user_id: int,
    db: AsyncSession,
    days_ago: int = 0,
    mode: str = "empathetic",
    is_user_message: bool = True
):
    """Tworzy wpis w historii konwersacji"""
    conversation = ConversationHistory(
        user_id=user_id,
        mode=mode,
        message="Test message",
        is_user_message=is_user_message,
        created_at=datetime.utcnow() - timedelta(days=days_ago)
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def create_api_hit(
    user_id: int,
    db: AsyncSession,
    endpoint: str = "/api/test",
    method: str = "GET",
    response_status: int = 200,
    response_time_ms: float = 100.0,
    days_ago: int = 0
):
    """Tworzy wpis API hit"""
    api_hit = ApiHit(
        user_id=user_id,
        endpoint=endpoint,
        method=method,
        ip_address="127.0.0.1",
        user_agent="test-agent",
        response_status=response_status,
        response_time_ms=response_time_ms,
        created_at=datetime.utcnow() - timedelta(days=days_ago)
    )
    db.add(api_hit)
    await db.commit()
    await db.refresh(api_hit)
    return api_hit


async def create_system_metric(
    db: AsyncSession,
    metric_name: str = "cpu_usage",
    metric_value: float = 50.0,
    metric_unit: str = "percent",
    days_ago: int = 0
):
    """Tworzy metrykę systemową"""
    metric = SystemMetrics(
        metric_name=metric_name,
        metric_value=metric_value,
        metric_unit=metric_unit,
        metric_metadata={"test": True},
        created_at=datetime.utcnow() - timedelta(days=days_ago)
    )
    db.add(metric)
    await db.commit()
    await db.refresh(metric)
    return metric


async def create_psychological_test(
    user_id: int,
    db: AsyncSession,
    test_type: str = "phq9",
    score: float = 5.0,
    days_ago: int = 0
):
    """Tworzy test psychologiczny"""
    test = PsychologicalTest(
        user_id=user_id,
        test_type=test_type,
        answers={"test": "data"},
        score=score,
        interpretation="Test interpretation",
        ai_analysis="Test analysis",
        created_at=datetime.utcnow() - timedelta(days=days_ago)
    )
    db.add(test)
    await db.commit()
    await db.refresh(test)
    return test


async def create_llm_metric(
    user_id: int,
    db: AsyncSession,
    endpoint: str = "empathetic",
    model_name: str = "llama3.2",
    response_time_ms: float = 1500.0,
    prompt_tokens: int = 50,
    completion_tokens: int = 100,
    success: bool = True,
    days_ago: int = 0
):
    """Tworzy metrykę LLM"""
    metric = LLMMetrics(
        user_id=user_id,
        endpoint=endpoint,
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        response_time_ms=response_time_ms,
        temperature=0.1,
        success=success,
        created_at=datetime.utcnow() - timedelta(days=days_ago)
    )
    db.add(metric)
    await db.commit()
    await db.refresh(metric)
    return metric


# ================== OVERVIEW TESTS ==================
@pytest.mark.asyncio
async def test_get_dashboard_overview_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i użytkowników
    admin = await create_admin_user(user_data, db_session)
    user1 = await create_regular_user(user_data, db_session, "1")
    user2 = await create_regular_user(user_data, db_session, "2")
    
    # Utwórz wpisy w dzienniku
    await create_diary_entry(user1.id, db_session)
    await create_diary_entry(user1.id, db_session, days_ago=10)
    await create_diary_entry(user2.id, db_session)
    
    # Utwórz konwersacje
    await create_conversation(user1.id, db_session)
    await create_conversation(user1.id, db_session, is_user_message=False)
    await create_conversation(user2.id, db_session, days_ago=10)

    # Utwórz metryki LLM
    await create_llm_metric(admin.id, db_session, "empathetic", "llama3.2", 1500.0, 50, 100, True, 0)
    await create_llm_metric(admin.id, db_session, "practical", "llama3.2", 2000.0, 60, 120, True, 1)
    await create_llm_metric(user1.id, db_session, "ai_analysis", "llama3.2", 3000.0, 100, 200, True, 2)

    # Pobierz token dostępu dla admina
    access_token = auth_service.create_token(
        subject=admin.username,
        scope="access_token"
    )

    # Wykonaj zapytanie
    response = await client.get(
        "/api/admin/stats/overview",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()

    # Sprawdź statystyki użytkowników
    assert data["users"]["total"] == 3  # admin + 2 użytkowników
    assert data["users"]["admins"] == 1
    assert data["users"]["active"] == 3  # domyślnie wszyscy aktywni
    assert data["users"]["confirmed"] == 1  # tylko admin jest potwierdzony

    # Sprawdź statystyki dziennika
    assert data["diary"]["total_entries"] == 3
    assert data["diary"]["recent_7_days"] == 2  # 2 wpisy w ostatnim tygodniu

    # Sprawdź statystyki konwersacji
    assert data["conversations"]["total"] == 3
    assert data["conversations"]["recent_7_days"] == 2

    # Sprawdź nowe statystyki API
    assert "api" in data
    assert "total_hits" in data["api"]
    assert "hits_24h" in data["api"]
    assert "avg_response_time_24h_ms" in data["api"]

    # Sprawdź nowe statystyki testów
    assert "tests" in data
    assert "total" in data["tests"]
    assert "recent_7_days" in data["tests"]

    # Sprawdź statystyki LLM
    assert "llm" in data
    assert "total_calls" in data["llm"]
    assert "calls_24h" in data["llm"]
    assert "avg_response_time_24h_ms" in data["llm"]
    assert "avg_response_time_7d_ms" in data["llm"]
    assert "avg_response_time_30d_ms" in data["llm"]


@pytest.mark.asyncio
async def test_get_dashboard_overview_as_regular_user(
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

    # Próba dostępu do przeglądu
    response = await client.get(
        "/api/admin/stats/overview",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 403
    assert "Brak uprawnień administratora" in response.json()["detail"]


# ================== USER STATISTICS TESTS ==================
@pytest.mark.asyncio
async def test_get_users_statistics_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i użytkowników
    admin = await create_admin_user(user_data, db_session)
    user1 = await create_regular_user(user_data, db_session, "1")
    user2 = await create_regular_user(user_data, db_session, "2")
    
    # Utwórz aktywność dla użytkowników
    await create_diary_entry(user1.id, db_session)
    await create_diary_entry(user1.id, db_session)
    await create_diary_entry(user2.id, db_session)
    
    await create_conversation(user1.id, db_session)
    await create_conversation(user2.id, db_session)

    access_token = auth_service.create_token(
        subject=admin.username,
        scope="access_token"
    )

    # Pobierz statystyki
    response = await client.get(
        "/api/admin/stats/users/stats",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()

    # Sprawdź statystyki użytkowników według statusu
    status_stats = data["users_by_status"]
    assert len(status_stats) > 0

    # Sprawdź rejestracje według dnia
    registrations = data["registrations_by_day"]
    assert len(registrations) > 0

    # Sprawdź top aktywnych użytkowników
    top_users = data["top_active_users"]
    assert len(top_users) > 0
    # Użytkownik1 powinien być najbardziej aktywny
    assert top_users[0]["diary_count"] == 2


# ================== DIARY STATISTICS TESTS ==================
@pytest.mark.asyncio
async def test_get_diary_statistics_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i użytkowników
    admin = await create_admin_user(user_data, db_session)
    user1 = await create_regular_user(user_data, db_session, "1")
    user2 = await create_regular_user(user_data, db_session, "2")
    
    # Utwórz wpisy w dzienniku z różnymi tagami
    entry1 = await create_diary_entry(user1.id, db_session)
    entry1.emotion_tags = "happy,excited"
    entry2 = await create_diary_entry(user1.id, db_session)
    entry2.emotion_tags = "happy,calm"
    entry3 = await create_diary_entry(user2.id, db_session)
    entry3.emotion_tags = "sad,anxious"
    await db_session.commit()

    access_token = auth_service.create_token(
        subject=admin.username,
        scope="access_token"
    )

    # Pobierz statystyki
    response = await client.get(
        "/api/admin/stats/diary/stats",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()

    # Sprawdź wpisy według dnia
    entries_by_day = data["entries_by_day"]
    assert len(entries_by_day) > 0

    # Sprawdź wpisy według użytkownika
    entries_by_user = data["entries_by_user"]
    assert len(entries_by_user) > 0
    # Użytkownik1 powinien mieć więcej wpisów
    assert entries_by_user[0]["entry_count"] == 2

    # Sprawdź analizę tagów
    emotion_tags = data["emotion_tags"]
    assert emotion_tags["total_tags"] == 6  # łącznie 6 tagów
    assert emotion_tags["unique_tags"] == 5  # 5 unikalnych tagów: happy, excited, calm, sad, anxious
    assert len(emotion_tags["top_tags"]) > 0
    # "happy" powinien być najczęstszym tagiem
    assert emotion_tags["top_tags"][0]["tag"] == "happy"
    assert emotion_tags["top_tags"][0]["count"] == 2


# ================== CONVERSATION STATISTICS TESTS ==================
@pytest.mark.asyncio
async def test_get_conversations_statistics_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i użytkowników
    admin = await create_admin_user(user_data, db_session)
    user1 = await create_regular_user(user_data, db_session, "1")
    user2 = await create_regular_user(user_data, db_session, "2")
    
    # Utwórz konwersacje w różnych trybach
    await create_conversation(
        user1.id,
        db_session,
        mode="empathetic",
        is_user_message=True
    )
    await create_conversation(
        user1.id,
        db_session,
        mode="empathetic",
        is_user_message=False
    )
    await create_conversation(
        user2.id,
        db_session,
        mode="practical",
        is_user_message=True
    )

    access_token = auth_service.create_token(
        subject=admin.username,
        scope="access_token"
    )

    # Pobierz statystyki
    response = await client.get(
        "/api/admin/stats/conversations/stats",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()

    # Sprawdź konwersacje według trybu
    by_mode = data["conversations_by_mode"]
    assert len(by_mode) == 2  # empathetic i practical
    empathetic_mode = next(
        m for m in by_mode if m["mode"] == "empathetic"
    )
    assert empathetic_mode["count"] == 2

    # Sprawdź konwersacje według dnia
    by_day = data["conversations_by_day"]
    assert len(by_day) > 0

    # Sprawdź konwersacje według użytkownika
    by_user = data["conversations_by_user"]
    assert len(by_user) > 0
    assert by_user[0]["conversation_count"] == 2  # user1 ma 2 konwersacje

    # Sprawdź rozkład wiadomości
    msg_dist = data["message_distribution"]
    assert msg_dist["user_messages"] == 2
    assert msg_dist["ai_messages"] == 1
    assert msg_dist["total_messages"] == 3


# ================== SYSTEM HEALTH TESTS ==================
@pytest.mark.asyncio
async def test_get_system_health_as_admin(
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

    # Sprawdź status systemu
    response = await client.get(
        "/api/admin/stats/system/health",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()

    assert "timestamp" in data
    assert "database" in data
    assert data["database"]["status"] == "healthy"
    assert data["overall_status"] == "healthy"


# ================== ALL DATA TESTS ==================
@pytest.mark.asyncio
async def test_get_all_system_data_as_admin(
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

    # Pobierz wszystkie dane
    response = await client.get(
        "/api/admin/stats/all-data",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()

    # Sprawdź czy wszystkie sekcje są obecne
    assert "overview" in data
    assert "users" in data
    assert "diary" in data
    assert "conversations" in data
    assert "api" in data
    assert "performance" in data
    assert "tests" in data
    assert "system_health" in data
    assert "timestamp" in data


# ================== EXPORT TESTS ==================
@pytest.mark.asyncio
async def test_export_system_data_as_admin(
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

    # Test eksportu JSON
    response = await client.get(
        "/api/admin/stats/export?format=json",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["format"] == "json"
    assert "data" in json_data
    assert "filename" in json_data
    assert json_data["filename"].endswith(".json")

    # Test eksportu CSV
    response = await client.get(
        "/api/admin/stats/export?format=csv",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    csv_data = response.json()
    assert csv_data["format"] == "csv"
    assert "data" in csv_data
    assert "filename" in csv_data
    assert csv_data["filename"].endswith(".csv")

    # Test eksportu XML
    response = await client.get(
        "/api/admin/stats/export?format=xml",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    xml_data = response.json()
    assert xml_data["format"] == "xml"
    assert "data" in xml_data
    assert "filename" in xml_data
    assert xml_data["filename"].endswith(".xml")


@pytest.mark.asyncio
async def test_export_system_data_invalid_format(
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

    # Test nieistniejącego formatu (powinien zwrócić JSON)
    response = await client.get(
        "/api/admin/stats/export?format=invalid",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["format"] == "json"  # domyślny format
    assert "data" in data
    assert data["filename"].endswith(".json")


# ================== API STATISTICS TESTS ==================
@pytest.mark.asyncio
async def test_get_api_statistics_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i użytkowników
    admin = await create_admin_user(user_data, db_session)
    user1 = await create_regular_user(user_data, db_session, "1")
    user2 = await create_regular_user(user_data, db_session, "2")
    
    # Utwórz API hits
    await create_api_hit(user1.id, db_session, "/api/echo", "POST", 200, 150.0)
    await create_api_hit(user1.id, db_session, "/api/echo", "POST", 200, 200.0)
    await create_api_hit(user2.id, db_session, "/api/users", "GET", 200, 100.0)
    await create_api_hit(user2.id, db_session, "/api/echo", "POST", 400, 300.0)  # Błąd

    access_token = auth_service.create_token(
        subject=admin.username,
        scope="access_token"
    )

    # Pobierz statystyki API
    response = await client.get(
        "/api/admin/stats/api/stats",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()

    # Sprawdź statystyki endpointów
    endpoint_stats = data["endpoint_stats"]
    assert len(endpoint_stats) > 0
    
    # Sprawdź statystyki statusów
    status_stats = data["status_stats"]
    assert len(status_stats) > 0
    
    # Sprawdź metryki błędów
    error_metrics = data["error_metrics"]
    assert error_metrics["error_count"] == 1
    assert error_metrics["total_requests"] == 4
    assert error_metrics["error_rate_percent"] == 25.0


# ================== PERFORMANCE STATISTICS TESTS ==================
@pytest.mark.asyncio
async def test_get_performance_statistics_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i użytkownika
    admin = await create_admin_user(user_data, db_session)
    user1 = await create_regular_user(user_data, db_session, "1")
    
    # Utwórz API hits z różnymi czasami odpowiedzi
    await create_api_hit(user1.id, db_session, "/api/echo", "POST", 200, 100.0)
    await create_api_hit(user1.id, db_session, "/api/echo", "POST", 200, 200.0)
    await create_api_hit(user1.id, db_session, "/api/users", "GET", 200, 50.0)
    
    # Utwórz metryki systemowe
    await create_system_metric(db_session, "cpu_usage", 75.0, "percent")
    await create_system_metric(db_session, "memory_usage", 60.0, "percent")

    access_token = auth_service.create_token(
        subject=admin.username,
        scope="access_token"
    )

    # Pobierz statystyki wydajności
    response = await client.get(
        "/api/admin/stats/performance/stats",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()

    # Sprawdź wydajność według godzin
    hourly_performance = data["hourly_performance"]
    assert len(hourly_performance) > 0
    
    # Sprawdź najwolniejsze endpointy
    slowest_endpoints = data["slowest_endpoints"]
    assert len(slowest_endpoints) > 0
    
    # Sprawdź metryki systemowe
    system_metrics = data["system_metrics"]
    assert len(system_metrics) > 0
    
    # Sprawdź percentyle
    percentiles = data["response_time_percentiles"]
    assert "p95_ms" in percentiles
    assert "p99_ms" in percentiles


# ================== TESTS STATISTICS TESTS ==================
@pytest.mark.asyncio
async def test_get_tests_statistics_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i użytkowników
    admin = await create_admin_user(user_data, db_session)
    user1 = await create_regular_user(user_data, db_session, "1")
    user2 = await create_regular_user(user_data, db_session, "2")
    
    # Utwórz testy psychologiczne
    await create_psychological_test(user1.id, db_session, "phq9", 5.0)
    await create_psychological_test(user1.id, db_session, "gad7", 8.0)
    await create_psychological_test(user2.id, db_session, "phq9", 12.0)
    await create_psychological_test(user2.id, db_session, "asrs", 15.0)

    access_token = auth_service.create_token(
        subject=admin.username,
        scope="access_token"
    )

    # Pobierz statystyki testów
    response = await client.get(
        "/api/admin/stats/tests/stats",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()

    # Sprawdź testy według typu
    tests_by_type = data["tests_by_type"]
    assert len(tests_by_type) == 3  # phq9, gad7, asrs
    
    # Sprawdź testy według dnia
    tests_by_day = data["tests_by_day"]
    assert len(tests_by_day) > 0
    
    # Sprawdź testy według użytkownika
    tests_by_user = data["tests_by_user"]
    assert len(tests_by_user) > 0
    
    # Sprawdź rozkład wyników
    score_distribution = data["score_distribution"]
    assert len(score_distribution) > 0


# ================== NEW ENDPOINTS ACCESS CONTROL TESTS ==================
@pytest.mark.asyncio
async def test_api_stats_access_control(
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

    # Próba dostępu do statystyk API
    response = await client.get(
        "/api/admin/stats/api/stats",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 403
    assert "Brak uprawnień administratora" in response.json()["detail"]


@pytest.mark.asyncio
async def test_performance_stats_access_control(
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

    # Próba dostępu do statystyk wydajności
    response = await client.get(
        "/api/admin/stats/performance/stats",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 403
    assert "Brak uprawnień administratora" in response.json()["detail"]


@pytest.mark.asyncio
async def test_tests_stats_access_control(
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

    # Próba dostępu do statystyk testów
    response = await client.get(
        "/api/admin/stats/tests/stats",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 403
    assert "Brak uprawnień administratora" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_llm_statistics_as_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz admina i użytkowników
    admin = await create_admin_user(user_data, db_session)
    user1 = await create_regular_user(user_data, db_session, "1")
    user2 = await create_regular_user(user_data, db_session, "2")
    
    # Utwórz metryki LLM
    await create_llm_metric(admin.id, db_session, "empathetic", "llama3.2", 1500.0, 50, 100, True, 0)
    await create_llm_metric(admin.id, db_session, "practical", "llama3.2", 2000.0, 60, 120, True, 1)
    await create_llm_metric(user1.id, db_session, "ai_analysis", "llama3.2", 3000.0, 100, 200, True, 2)
    await create_llm_metric(user2.id, db_session, "empathetic", "llama3.2", 1000.0, 40, 80, False, 0)  # błąd

    # Pobierz token dostępu dla admina
    access_token = auth_service.create_token(
        subject=admin.username,
        scope="access_token"
    )

    # Wykonaj zapytanie
    response = await client.get(
        "/api/admin/stats/llm/stats",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()

    # Sprawdź strukturę odpowiedzi
    assert "endpoint_stats" in data
    assert "model_stats" in data
    assert "daily_stats" in data
    assert "top_llm_users" in data
    assert "error_metrics" in data
    assert "token_metrics" in data
    assert "hourly_stats" in data
    assert "response_time_periods" in data
    assert "weekly_stats" in data

    # Sprawdź statystyki endpointów
    assert len(data["endpoint_stats"]) >= 2  # empathetic, practical, ai_analysis
    empathetic_stats = next((s for s in data["endpoint_stats"] if s["endpoint"] == "empathetic"), None)
    assert empathetic_stats is not None
    assert empathetic_stats["count"] == 2  # 1 sukces + 1 błąd
    assert empathetic_stats["avg_response_time_ms"] == 1250.0  # (1500 + 1000) / 2

    # Sprawdź statystyki modeli
    assert len(data["model_stats"]) >= 1
    llama_stats = next((s for s in data["model_stats"] if s["model_name"] == "llama3.2"), None)
    assert llama_stats is not None
    assert llama_stats["count"] == 4

    # Sprawdź metryki błędów
    assert data["error_metrics"]["error_count"] == 1
    assert data["error_metrics"]["total_calls"] == 4
    assert data["error_metrics"]["error_rate_percent"] == 25.0

    # Sprawdź metryki tokenów
    assert data["token_metrics"]["total_prompt_tokens"] == 250  # 50+60+100+40
    assert data["token_metrics"]["total_completion_tokens"] == 500  # 100+120+200+80
    assert data["token_metrics"]["total_tokens"] == 750

    # Sprawdź statystyki czasowe dla różnych okresów
    assert "avg_24h_ms" in data["response_time_periods"]
    assert "avg_7d_ms" in data["response_time_periods"]
    assert "avg_30d_ms" in data["response_time_periods"]
    assert isinstance(data["response_time_periods"]["avg_24h_ms"], (int, float))
    assert isinstance(data["response_time_periods"]["avg_7d_ms"], (int, float))
    assert isinstance(data["response_time_periods"]["avg_30d_ms"], (int, float))

    # Sprawdź statystyki tygodniowe
    assert isinstance(data["weekly_stats"], list)
    for week_stat in data["weekly_stats"]:
        assert "week" in week_stat
        assert "count" in week_stat
        assert "avg_response_time_ms" in week_stat
        assert "total_tokens" in week_stat


@pytest.mark.asyncio
async def test_get_llm_statistics_access_control(
    client: AsyncClient,
    db_session: AsyncSession,
    user_data
):
    # Utwórz zwykłego użytkownika
    user = await login_user_confirmed_true_and_hash_password(
        user_data,
        db_session
    )

    # Pobierz token dostępu
    access_token = auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

    # Wykonaj zapytanie
    response = await client.get(
        "/api/admin/stats/llm/stats",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 403
    assert "Brak uprawnień administratora" in response.json()["detail"]
