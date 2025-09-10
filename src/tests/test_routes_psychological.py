
import pytest
import pytest_asyncio
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from src.database.models import PsychologicalTest
from datetime import datetime
from src.tests.conftest import login_user_confirmed_true_and_hash_password
from src.services.auth import auth_service

# ================== Test Fixtures ==================

@pytest_asyncio.fixture
async def authenticated_user(db_session, user_data):
    """Tworzy uwierzytelnionego użytkownika w bazie danych"""
    return await login_user_confirmed_true_and_hash_password(user_data, db_session)

@pytest_asyncio.fixture
async def auth_headers(authenticated_user):
    """Tworzy nagłówki autoryzacji dla uwierzytelnionego użytkownika"""
    access_token = auth_service.create_token(subject=authenticated_user.username, scope="access_token")
    return {"Authorization": f"Bearer {access_token}"}

@pytest_asyncio.fixture
async def mock_test_result(authenticated_user, db_session):
    test_result = PsychologicalTest(
        id=1,
        user_id=authenticated_user.id,
        test_type="gad7",
        answers={"answers": [1, 2, 3, 1, 2, 3, 1]},
        score=13.0,
        interpretation="Umiarkowany lęk",
        ai_analysis="AI analysis text.",
        created_at=datetime.utcnow()
    )
    db_session.add(test_result)
    await db_session.commit()
    await db_session.refresh(test_result)
    return test_result

# ================== Test Submit Endpoints ==================

@pytest.mark.asyncio
@patch('src.routes.psychological_tests.PsychologicalTestService.calculate_asrs_score', return_value=(50.0, "Wysokie ryzyko ADHD"))
@patch('src.routes.psychological_tests.PsychologicalTestService.get_ai_analysis', new_callable=AsyncMock, return_value="AI analysis")
async def test_submit_asrs_test(mock_ai_analysis, mock_calculate_score, client: AsyncClient, db_session, auth_headers):
    response = await client.post("/api/tests/asrs", json={"part_a": [3]*6, "part_b": [1]*12}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data['interpretation'] == "Wysokie ryzyko ADHD"

@pytest.mark.asyncio
async def test_submit_asrs_invalid_answers(client: AsyncClient, auth_headers):
    response = await client.post("/api/tests/asrs", json={"part_a": [5]*6, "part_b": [1]*12}, headers=auth_headers)
    assert response.status_code == 400

@pytest.mark.asyncio
@patch('src.routes.psychological_tests.PsychologicalTestService.calculate_gad7_score', return_value=(13.0, "Umiarkowany lęk"))
@patch('src.routes.psychological_tests.PsychologicalTestService.get_ai_analysis', new_callable=AsyncMock, return_value="AI analysis")
async def test_submit_gad7_test(mock_ai_analysis, mock_calculate_score, client: AsyncClient, db_session, auth_headers):
    response = await client.post("/api/tests/gad7", json={"answers": [1, 2, 3, 1, 2, 3, 1]}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data['interpretation'] == "Umiarkowany lęk"

@pytest.mark.asyncio
async def test_submit_gad7_invalid_answers(client: AsyncClient, auth_headers):
    response = await client.post("/api/tests/gad7", json={"answers": [4, 1, 1, 1, 1, 1, 1]}, headers=auth_headers)
    assert response.status_code == 400

@pytest.mark.asyncio
@patch('src.routes.psychological_tests.PsychologicalTestService.calculate_phq9_score', return_value=(22.0, "Ciężka depresja"))
@patch('src.routes.psychological_tests.PsychologicalTestService.get_ai_analysis', new_callable=AsyncMock, return_value="AI analysis")
async def test_submit_phq9_test(mock_ai_analysis, mock_calculate_score, client: AsyncClient, db_session, auth_headers):
    response = await client.post("/api/tests/phq9", json={"answers": [3]*9}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data['interpretation'] == "Ciężka depresja"

@pytest.mark.asyncio
async def test_submit_phq9_invalid_answers(client: AsyncClient, auth_headers):
    response = await client.post("/api/tests/phq9", json={"answers": [4]*9}, headers=auth_headers)
    assert response.status_code == 400

# ================== Test History Endpoint ==================

@pytest.mark.asyncio
async def test_get_test_history(client: AsyncClient, mock_test_result, auth_headers):
    response = await client.get("/api/tests/history", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data['total_count'] == 1
    assert len(data['tests']) == 1

@pytest.mark.asyncio
async def test_get_test_history_with_filter(client: AsyncClient, mock_test_result, auth_headers):
    response = await client.get("/api/tests/history?test_type=gad7", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data['total_count'] == 1
    assert len(data['tests']) == 1
    
    response_empty = await client.get("/api/tests/history?test_type=asrs", headers=auth_headers)
    assert response_empty.status_code == 200
    data_empty = response_empty.json()
    assert data_empty['total_count'] == 0
    assert len(data_empty['tests']) == 0

# ================== Test Result Endpoint ==================

@pytest.mark.asyncio
async def test_get_test_result(client: AsyncClient, mock_test_result, auth_headers):
    response = await client.get(f"/api/tests/result/{mock_test_result.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data['id'] == mock_test_result.id

@pytest.mark.asyncio
async def test_get_test_result_not_found(client: AsyncClient, auth_headers):
    response = await client.get("/api/tests/result/999", headers=auth_headers)
    assert response.status_code == 404

# ================== Test Questions Endpoint ==================

@pytest.mark.asyncio
async def test_get_test_questions(client: AsyncClient, auth_headers):
    response = await client.get("/api/tests/questions/asrs", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "questions_part_a" in data

@pytest.mark.asyncio
async def test_get_test_questions_not_found(client: AsyncClient, auth_headers):
    response = await client.get("/api/tests/questions/invalid_test", headers=auth_headers)
    assert response.status_code == 422 # Unprocessable Entity for invalid enum value
