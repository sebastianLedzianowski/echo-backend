
import pytest
from unittest.mock import patch, AsyncMock
from src.services.psychological_tests import PsychologicalTestService


# ================== ASRS Score Calculation Tests ==================

def test_calculate_asrs_score_high_risk():
    answers = {'part_a': [3, 4, 3, 4, 2, 1], 'part_b': [1]*12}
    score, interpretation = PsychologicalTestService.calculate_asrs_score(answers)
    assert interpretation == "Wysokie ryzyko ADHD"
    assert isinstance(score, float)

def test_calculate_asrs_score_low_risk():
    answers = {'part_a': [1, 2, 1, 2, 2, 1], 'part_b': [1]*12}
    score, interpretation = PsychologicalTestService.calculate_asrs_score(answers)
    assert interpretation == "Niskie ryzyko ADHD"
    assert isinstance(score, float)

def test_calculate_asrs_score_empty_answers():
    answers = {}
    score, interpretation = PsychologicalTestService.calculate_asrs_score(answers)
    assert score == 0.0
    assert interpretation == "Brak odpowiedzi do analizy"


# ================== GAD-7 Score Calculation Tests ==================

@pytest.mark.parametrize("score_sum,expected_interpretation", [
    (3, "Minimalny poziom lęku"),
    (7, "Łagodny lęk"),
    (12, "Umiarkowany lęk"),
    (18, "Ciężki lęk"),
])
def test_calculate_gad7_score(score_sum, expected_interpretation):
    answers = {'answers': [score_sum] + [0]*6}  # Mocking answers to get the desired sum
    score, interpretation = PsychologicalTestService.calculate_gad7_score(answers)
    assert score == float(score_sum)
    assert interpretation == expected_interpretation


# ================== PHQ-9 Score Calculation Tests ==================

@pytest.mark.parametrize("score_sum,expected_interpretation", [
    (2, "Brak objawów depresji"),
    (8, "Łagodna depresja"),
    (13, "Umiarkowana depresja"),
    (17, "Umiarkowanie ciężka depresja"),
    (22, "Ciężka depresja"),
])
def test_calculate_phq9_score(score_sum, expected_interpretation):
    answers = {'answers': [score_sum] + [0]*8}
    score, interpretation = PsychologicalTestService.calculate_phq9_score(answers)
    assert score == float(score_sum)
    assert interpretation == expected_interpretation


# ================== AI Analysis Tests ==================

@pytest.mark.asyncio
@patch('src.services.psychological_tests.get_ai_analysis_response', new_callable=AsyncMock)
async def test_get_ai_analysis_asrs(mock_get_ai_response):
    mock_get_ai_response.return_value = "AI analysis for ASRS"
    answers = {'part_a': [3, 4, 3, 4, 0, 0], 'part_b': [0]*12}
    response = await PsychologicalTestService.get_ai_analysis("asrs", answers, 50.0, "Wysokie ryzyko ADHD")
    assert response == "AI analysis for ASRS"
    mock_get_ai_response.assert_called_once()

@pytest.mark.asyncio
@patch('src.services.psychological_tests.get_ai_analysis_response', new_callable=AsyncMock)
async def test_get_ai_analysis_gad7(mock_get_ai_response):
    mock_get_ai_response.return_value = "AI analysis for GAD-7"
    answers = {'answers': [3]*7}
    response = await PsychologicalTestService.get_ai_analysis("gad7", answers, 21.0, "Ciężki lęk")
    assert response == "AI analysis for GAD-7"
    mock_get_ai_response.assert_called_once()

@pytest.mark.asyncio
@patch('src.services.psychological_tests.get_ai_analysis_response', new_callable=AsyncMock)
async def test_get_ai_analysis_phq9(mock_get_ai_response):
    mock_get_ai_response.return_value = "AI analysis for PHQ-9"
    answers = {'answers': [3]*9}
    response = await PsychologicalTestService.get_ai_analysis("phq9", answers, 27.0, "Ciężka depresja")
    assert response == "AI analysis for PHQ-9"
    mock_get_ai_response.assert_called_once()

@pytest.mark.asyncio
@patch('src.services.psychological_tests.get_ai_analysis_response', new_callable=AsyncMock)
async def test_get_ai_analysis_phq9_suicidal_thoughts(mock_get_ai_response):
    mock_get_ai_response.return_value = "AI analysis for PHQ-9 with suicidal thoughts"
    answers = {'answers': [1]*8 + [3]}
    await PsychologicalTestService.get_ai_analysis("phq9", answers, 11.0, "Umiarkowana depresja")
    
    # Check if the prompt contains the critical warning
    call_args, _ = mock_get_ai_response.call_args
    prompt = call_args[0]
    assert "KRYTYCZNE: Wysokie ryzyko myśli samobójczych" in prompt

@pytest.mark.asyncio
@patch('src.services.psychological_tests.get_ai_analysis_response', side_effect=Exception("AI service error"))
async def test_get_ai_analysis_exception(mock_get_ai_response):
    answers = {'answers': [1]*7}
    interpretation = "Łagodny lęk"
    response = await PsychologicalTestService.get_ai_analysis("gad7", answers, 7.0, interpretation)
    
    assert "Nie udało się wygenerować szczegółowej analizy" in response
    assert interpretation in response
