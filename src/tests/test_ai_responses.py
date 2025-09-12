import httpx
import pytest
import asyncio
import time
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.ai import (
    AIServiceError,
    generate_empathetic_response,
    generate_practical_response,
    _prepare_conversation_context,
    _prepare_chat_messages,
    _call_ollama_chat_api,
    _call_ollama_generate_api,
    get_ai_response,
    get_ai_analysis_response,
    save_llm_metrics,
    estimate_tokens,
    save_conversation_message,
    save_diary_entry,
    get_conversation_history,
    check_ollama_connection,
    SYSTEM_PROMPT_EMPATHETIC,
    SYSTEM_PROMPT_PRACTICAL,
    OLLAMA_URL,
    OLLAMA_MODEL
)

# Przykładowa historia rozmowy
sample_history = [
    {"message": "Miałem ciężki dzień.", "is_user_message": True},
    {"message": "Rozumiem, to musiało być trudne.", "is_user_message": False},
]

try:
    from src.services.metrics import record_conversation, record_diary_entry

    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False


# ================== TESTY PODSTAWOWYCH FUNKCJI ==================
@pytest.mark.asyncio
async def test_generate_empathetic_response():
    user_input = "Czuję się bardzo zmęczony."

    # Mock odpowiedzi AI
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "message": {
                    "content": "Rozumiem, że czujesz się zmęczony. Czy możesz mi powiedzieć więcej?"
                }
            }
        )

        response = await generate_empathetic_response(user_input, sample_history)
        print("\n[Empatyczna odpowiedź] ->", response)
        assert isinstance(response, str)
        assert len(response.strip()) > 0
        # Odpowiedź powinna mieć co najmniej 5 słów
        assert len(response.split()) >= 5
        # Odpowiedź powinna kończyć się znakiem interpunkcyjnym
        assert response.endswith((".", "!", "?"))


@pytest.mark.asyncio
async def test_generate_practical_response():
    user_input = "Jak mogę lepiej zarządzać czasem?"

    # Mock odpowiedzi AI
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "message": {
                    "content": "Oto kilka wskazówek:\n- Planuj zadania z wyprzedzeniem\n- Ustal priorytety\n- Rób regularne przerwy"
                }
            }
        )

        response = await generate_practical_response(user_input, sample_history)
        print("\n[Praktyczna odpowiedź] ->", response)
        assert isinstance(response, str)
        assert len(response.strip()) > 0
        # Praktyczna odpowiedź powinna być bardziej rozbudowana
        assert len(response.split()) >= 10
        # Format punktowy
        assert any(
            line.strip().startswith(("-", "•", "*", "1.", "2."))
            for line in response.split("\n")
        )


# ================== TESTY POMOCNICZYCH FUNKCJI ==================
def test_prepare_conversation_context():
    # Test pustej historii
    empty_context = _prepare_conversation_context(None)
    assert empty_context == "Brak wcześniejszej historii rozmowy."

    # Test krótkiej historii
    short_history = [
        {"message": "Cześć", "is_user_message": True},
        {"message": "Witaj!", "is_user_message": False}
    ]
    short_context = _prepare_conversation_context(short_history)
    assert "Użytkownik: Cześć" in short_context
    assert "AI: Witaj!" in short_context

    # Test długiej historii (powinno zwrócić tylko ostatnie 5 wiadomości)
    long_history = [
        {
            "message": f"Wiadomość {i}",
            "is_user_message": i % 2 == 0
        } for i in range(10)
    ]
    long_context = _prepare_conversation_context(long_history)
    assert len(long_context.split("\n")) == 5


def test_prepare_chat_messages():
    prompt = "Test prompt"
    system_prompt = "Test system prompt"

    # Test bez historii
    messages = _prepare_chat_messages(prompt, system_prompt)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == system_prompt
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == prompt

    # Test z historią
    messages_with_history = _prepare_chat_messages(
        prompt, system_prompt, sample_history
    )
    assert len(messages_with_history) == 4
    assert messages_with_history[0]["role"] == "system"
    assert messages_with_history[1]["role"] == "user"
    assert messages_with_history[2]["role"] == "assistant"
    assert messages_with_history[3]["role"] == "user"
    assert messages_with_history[3]["content"] == prompt

    # Test z pustą historią
    empty_history_messages = _prepare_chat_messages(prompt, system_prompt, [])
    assert len(empty_history_messages) == 2


def test_estimate_tokens():
    # Test podstawowego szacowania
    assert estimate_tokens("test") == 1
    assert estimate_tokens("") == 1  # minimum 1 token
    assert estimate_tokens("a" * 8) == 2  # 8 znaków = 2 tokeny
    assert estimate_tokens("test message with more words") >= 7


# ================== TESTY SAVE_LLM_METRICS ==================
@pytest.mark.asyncio
async def test_save_llm_metrics_success():
    mock_db = AsyncMock(spec=AsyncSession)

    await save_llm_metrics(
        user_id=1,
        endpoint="test",
        model_name="test_model",
        response_time_ms=100.0,
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        cost_usd=0.01,
        temperature=0.1,
        max_tokens=100,
        success=True,
        db=mock_db
    )

    # Sprawdź czy metryki zostały dodane i commitowane
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_save_llm_metrics_no_db():
    # Test gdy db=None - nie powinno nic robić
    await save_llm_metrics(
        user_id=1,
        endpoint="test",
        model_name="test_model",
        response_time_ms=100.0,
        db=None
    )
    # Nie powinno rzucić wyjątku


@pytest.mark.asyncio
async def test_save_llm_metrics_db_error():
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.commit.side_effect = Exception("DB Error")

    # Nie powinno rzucić wyjątku - błąd jest obsłużony
    await save_llm_metrics(
        user_id=1,
        endpoint="test",
        model_name="test_model",
        response_time_ms=100.0,
        db=mock_db
    )

    mock_db.rollback.assert_called_once()


# ================== TESTY GET_AI_RESPONSE ==================
@pytest.mark.asyncio
async def test_get_ai_response_empathetic():
    with patch("src.services.ai._call_ollama_chat_api") as mock_call:
        mock_call.return_value = "Empatyczna odpowiedź"

        response = await get_ai_response("test", mode="empathetic")

        assert response == "Empatyczna odpowiedź"
        mock_call.assert_called_once_with(
            "test",
            SYSTEM_PROMPT_EMPATHETIC,
            "empathetic",
            user_id=None,
            endpoint="ai_response",
            db=None
        )


@pytest.mark.asyncio
async def test_get_ai_response_practical():
    with patch("src.services.ai._call_ollama_chat_api") as mock_call:
        mock_call.return_value = "Praktyczna odpowiedź"

        response = await get_ai_response("test", mode="practical")

        assert response == "Praktyczna odpowiedź"
        mock_call.assert_called_once_with(
            "test",
            SYSTEM_PROMPT_PRACTICAL,
            "practical",
            user_id=None,
            endpoint="ai_response",
            db=None
        )


@pytest.mark.asyncio
async def test_get_ai_response_other_mode():
    with patch("src.services.ai._call_ollama_generate_api") as mock_call:
        mock_call.return_value = "Generate odpowiedź"

        response = await get_ai_response("test", mode="other")

        assert response == "Generate odpowiedź"
        mock_call.assert_called_once_with(
            "test",
            SYSTEM_PROMPT_EMPATHETIC,
            user_id=None,
            endpoint="ai_response",
            db=None
        )


# ================== TESTY GET_AI_ANALYSIS_RESPONSE ==================
@pytest.mark.asyncio
async def test_get_ai_analysis_response():
    with patch("src.services.ai._call_ollama_chat_api") as mock_call:
        mock_call.return_value = "Analiza psychologiczna"

        response = await get_ai_analysis_response("test prompt")

        assert response == "Analiza psychologiczna"
        mock_call.assert_called_once()
        # Sprawdź czy został użyty system prompt dla analizy psychologicznej
        call_args = mock_call.call_args[0]
        assert "psychologiem klinicznym" in call_args[1]


# ================== TESTY OBSŁUGI BŁĘDÓW W _CALL_OLLAMA_CHAT_API ==================
@pytest.mark.asyncio
async def test_call_ollama_chat_api_empty_response():
    """Test obsługi pustej odpowiedzi od API"""
    with patch('httpx.AsyncClient.post') as mock_post:
        # Symuluj odpowiedź z pustą wiadomością
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"message": {"content": "   "}}
        )

        with patch("src.services.ai.LLMMetricsContext"):
            with pytest.raises(AIServiceError) as exc_info:
                await _call_ollama_chat_api("Test", SYSTEM_PROMPT_EMPATHETIC, "test")
            assert exc_info.value.error_type == "empty_response"


@pytest.mark.asyncio
async def test_call_ollama_chat_api_model_not_found():
    """Test obsługi błędu braku modelu"""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=404,
            text="Model not found"
        )

        with patch("src.services.ai.LLMMetricsContext"):
            with pytest.raises(AIServiceError) as exc_info:
                await _call_ollama_chat_api("Test", SYSTEM_PROMPT_EMPATHETIC, "test")
            assert exc_info.value.error_type == "model_not_found"


@pytest.mark.asyncio
async def test_call_ollama_chat_api_timeout_with_retry():
    """Test mechanizmu retry przy timeout"""
    with patch('httpx.AsyncClient.post') as mock_post:
        # Pierwsze dwa wywołania zwracają timeout, trzecie sukces
        mock_post.side_effect = [
            httpx.TimeoutException("Timeout"),
            httpx.TimeoutException("Timeout"),
            AsyncMock(
                status_code=200,
                json=lambda: {"message": {"content": "Udana odpowiedź"}}
            )
        ]

        with patch("src.services.ai.LLMMetricsContext"):
            with patch("asyncio.sleep"):  # Skip actual sleep
                response = await _call_ollama_chat_api("Test", SYSTEM_PROMPT_EMPATHETIC, "test")
                assert response == "Udana odpowiedź"
                assert mock_post.call_count == 3


@pytest.mark.asyncio
async def test_call_ollama_chat_api_all_retries_fail():
    """Test gdy wszystkie retry się nie powiodą"""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Persistent timeout")

        with patch("src.services.ai.LLMMetricsContext"):
            with patch("asyncio.sleep"):
                with pytest.raises(httpx.TimeoutException):
                    await _call_ollama_chat_api("Test", SYSTEM_PROMPT_EMPATHETIC, "test")
                assert mock_post.call_count == 3  # RETRY_COUNT = 3


# ================== TESTY _CALL_OLLAMA_GENERATE_API ==================
@pytest.mark.asyncio
async def test_call_ollama_generate_api_success():
    """Test udanego wywołania Generate API"""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"response": "Generate response"}
        )

        response = await _call_ollama_generate_api("Test prompt", "System prompt")
        assert response == "Generate response"


@pytest.mark.asyncio
async def test_call_ollama_generate_api_empty_response():
    """Test pustej odpowiedzi z Generate API"""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"response": ""}
        )

        with patch("asyncio.sleep"):
            with pytest.raises(AIServiceError) as exc_info:
                await _call_ollama_generate_api("Test prompt")
            # Sprawdź message zamiast error_type dla generate API
            assert "Otrzymano pustą odpowiedź" in str(exc_info.value)


@pytest.mark.asyncio
async def test_call_ollama_generate_api_http_error():
    """Test błędu HTTP z Generate API"""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=500,
            text="Internal Server Error",
            json=lambda: {"error": "Server error"}
        )

        with patch("asyncio.sleep"):
            with pytest.raises(AIServiceError) as exc_info:
                await _call_ollama_generate_api("Test prompt")
            # Sprawdź message zamiast error_type
            assert "Błąd API" in str(exc_info.value)


@pytest.mark.asyncio
async def test_call_ollama_generate_api_connection_error():
    """Test błędu połączenia w Generate API"""
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_post.side_effect = httpx.RequestError("Connection failed")

        with patch("asyncio.sleep"):
            with pytest.raises(AIServiceError) as exc_info:
                await _call_ollama_generate_api("Test prompt")
            # Sprawdź message zamiast error_type
            assert "Błąd połączenia" in str(exc_info.value)


# ================== TESTY SAVE_CONVERSATION_MESSAGE ==================
@pytest.mark.asyncio
async def test_save_conversation_message_basic():
    """Test podstawowego zapisania wiadomości (bez metrics)"""
    mock_db = AsyncMock(spec=AsyncSession)

    await save_conversation_message(
        user_id=1,
        mode="empathetic",
        message="Test message",
        is_user_message=True,
        db=mock_db
    )

    # Sprawdź tylko operacje na bazie danych
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_save_conversation_message_ai_message():
    """Test zapisania wiadomości AI (nie powinno recordować metryki)"""
    mock_db = AsyncMock(spec=AsyncSession)

    with patch("src.services.metrics.record_conversation") as mock_record:
        await save_conversation_message(
            user_id=1,
            mode="empathetic",
            message="AI response",
            is_user_message=False,
            db=mock_db
        )

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_record.assert_not_called()


@pytest.mark.asyncio
async def test_save_conversation_message_db_error():
    """Test obsługi błędu bazy danych"""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.commit.side_effect = Exception("DB Error")

    with pytest.raises(Exception):
        await save_conversation_message(
            user_id=1,
            mode="empathetic",
            message="Test message",
            is_user_message=True,
            db=mock_db
        )

    mock_db.rollback.assert_called_once()


# ================== TESTY SAVE_DIARY_ENTRY ==================
@pytest.mark.asyncio
async def test_save_diary_entry_basic():
    """Test podstawowego zapisania wpisu do dziennika (bez metrics)"""
    mock_db = AsyncMock(spec=AsyncSession)

    entry = await save_diary_entry(
        user_id=1,
        content="Dzisiejszy dzień był trudny",
        title="Mój dzień",
        db=mock_db
    )

    assert entry.user_id == 1
    assert entry.content == "Dzisiejszy dzień był trudny"
    assert entry.title == "Mój dzień"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_save_diary_entry_without_db():
    """Test zapisania wpisu bez bazy danych"""
    entry = await save_diary_entry(
        user_id=1,
        content="Test content",
        db=None
    )

    assert entry.user_id == 1
    assert entry.content == "Test content"
    assert entry.title is None


@pytest.mark.asyncio
async def test_save_diary_entry_db_error():
    """Test obsługi błędu bazy danych przy zapisie dziennika"""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.commit.side_effect = Exception("DB Error")

    with pytest.raises(Exception):
        await save_diary_entry(
            user_id=1,
            content="Test content",
            db=mock_db
        )

    mock_db.rollback.assert_called_once()


# ================== TESTY GET_CONVERSATION_HISTORY ==================
@pytest.mark.asyncio
async def test_get_conversation_history_success():
    """Test pobierania historii konwersacji"""
    mock_db = AsyncMock(spec=AsyncSession)

    # Mock wyników z bazy danych - popraw strukturę mock'a
    mock_entry1 = MagicMock()
    mock_entry1.message = "Wiadomość 1"
    mock_entry1.is_user_message = True
    mock_entry1.created_at.isoformat.return_value = "2024-01-01T10:00:00"

    mock_entry2 = MagicMock()
    mock_entry2.message = "Wiadomość 2"
    mock_entry2.is_user_message = False
    mock_entry2.created_at.isoformat.return_value = "2024-01-01T10:01:00"

    # Popraw mock result
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_entry2, mock_entry1]  # Odwrotna kolejność

    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars

    mock_db.execute.return_value = mock_result

    history = await get_conversation_history(
        user_id=1,
        mode="empathetic",
        db=mock_db,
        limit=20
    )

    assert len(history) == 2
    # Sprawdź czy historia jest posortowana chronologicznie
    assert history[0]["message"] == "Wiadomość 1"
    assert history[1]["message"] == "Wiadomość 2"
    assert history[0]["is_user_message"] is True
    assert history[1]["is_user_message"] is False


@pytest.mark.asyncio
async def test_get_conversation_history_db_error():
    """Test obsługi błędu przy pobieraniu historii"""
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.execute.side_effect = Exception("DB Error")

    history = await get_conversation_history(
        user_id=1,
        mode="empathetic",
        db=mock_db
    )

    assert history == []


# ================== TESTY TEST_OLLAMA_CONNECTION ==================
def test_ollama_config():
    """Test konfiguracji Ollama"""
    from src.services.ai import OLLAMA_URL, OLLAMA_MODEL, RETRY_COUNT, REQUEST_TIMEOUT

    assert OLLAMA_URL is not None
    assert OLLAMA_MODEL is not None
    assert isinstance(OLLAMA_URL, str)
    assert isinstance(OLLAMA_MODEL, str)
    assert len(OLLAMA_URL) > 0
    assert len(OLLAMA_MODEL) > 0
    assert RETRY_COUNT > 0
    assert REQUEST_TIMEOUT > 0


def test_ollama_connection_sync():
    """Test konfiguracji połączenia z Ollama (synchroniczny)"""
    from src.services.ai import OLLAMA_URL, OLLAMA_MODEL

    # Test podstawowych konfiguracji
    assert OLLAMA_URL is not None
    assert OLLAMA_MODEL is not None
    assert isinstance(OLLAMA_URL, str)
    assert isinstance(OLLAMA_MODEL, str)
    assert len(OLLAMA_URL) > 0
    assert len(OLLAMA_MODEL) > 0


@pytest.mark.asyncio
async def test_test_ollama_connection_model_not_loaded():
    """Test gdy model nie jest załadowany"""
    with patch('httpx.AsyncClient.get') as mock_get, \
            patch('httpx.AsyncClient.post') as mock_post:
        # Mock odpowiedzi /api/tags bez naszego modelu
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"models": [{"name": "other_model"}]}
        )

        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"message": {"content": "response"}}
        )

        result = await check_ollama_connection()

        assert result["model_loaded"] is False
        assert any("nie jest załadowany" in error for error in result["errors"])


@pytest.mark.asyncio
async def test_test_ollama_connection_api_errors():
    """Test błędów API"""
    with patch('httpx.AsyncClient.get') as mock_get, \
            patch('httpx.AsyncClient.post') as mock_post:
        mock_get.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"models": [{"name": OLLAMA_MODEL}]}
        )

        # Mock błędów API
        mock_post.return_value = AsyncMock(
            status_code=500,
            text="Server Error"
        )

        result = await check_ollama_connection()

        assert result["chat_api_working"] is False
        assert result["generate_api_working"] is False
        assert len(result["errors"]) >= 2  # Błąd dla chat i generate API


@pytest.mark.asyncio
async def test_test_ollama_connection_connection_error():
    """Test błędu połączenia"""
    with patch('httpx.AsyncClient.get') as mock_get:
        mock_get.side_effect = Exception("Connection failed")

        result = await check_ollama_connection()

        assert len(result["errors"]) > 0
        assert any("Connection error" in error for error in result["errors"])


# ================== TESTY EDGE CASES ==================
@pytest.mark.asyncio
async def test_conversation_with_very_long_history():
    """Test z bardzo długą historią konwersacji"""
    long_history = [
        {
            "message": f"Message {i}",
            "is_user_message": i % 2 == 0
        } for i in range(100)
    ]

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"message": {"content": "Response"}}
        )

        # Sprawdź czy funkcja radzi sobie z długą historią
        response = await generate_empathetic_response("Test", long_history)
        assert response == "Response"

        # Sprawdź czy tylko ostatnie 5 wiadomości zostały użyte
        call_args = mock_post.call_args[1]["json"]["messages"]
        # system + 5 ostatnich z historii + current prompt = 7
        assert len(call_args) == 7


@pytest.mark.asyncio
async def test_empty_user_input():
    """Test z pustym wejściem użytkownika"""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"message": {"content": "Jak mogę ci pomóc?"}}
        )

        response = await generate_empathetic_response("")
        assert response == "Jak mogę ci pomóc?"


@pytest.mark.asyncio
async def test_special_characters_in_input():
    """Test ze specjalnymi znakami w wejściu"""
    special_input = "Test z emotikonami 😊 i znakami: @#$%^&*()"

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"message": {"content": "Rozumiem emotikony"}}
        )

        response = await generate_empathetic_response(special_input)
        assert response == "Rozumiem emotikony"


# ================== TESTY AISERVICEERROR ==================
def test_aiservice_error_creation():
    """Test tworzenia wyjątku AIServiceError"""
    error = AIServiceError("Test message", "test_type")
    assert error.message == "Test message"
    assert error.error_type == "test_type"
    assert str(error) == "test_type: Test message"


def test_aiservice_error_default_type():
    """Test domyślnego typu błędu"""
    error = AIServiceError("Test message")
    assert error.error_type == "general"
    assert str(error) == "general: Test message"


# ================== TESTY PERFORMANCE ==================
@pytest.mark.asyncio
async def test_response_time_measurement():
    """Test mierzenia czasu odpowiedzi"""
    with patch("httpx.AsyncClient.post") as mock_post, \
            patch("src.services.ai.save_llm_metrics") as mock_save, \
            patch("src.services.ai.LLMMetricsContext") as mock_context:
        # Mock context manager
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=None)
        mock_context.return_value = mock_ctx

        # Symuluj czas
        with patch("time.time", side_effect=[1000.0, 1000.5]):  # 500ms różnicy
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: {"message": {"content": "Test response"}}
            )

            mock_db = AsyncMock()
            response = await generate_empathetic_response(
                "Test", db=mock_db, user_id=1
            )

            # Sprawdź czy metryki zostały zapisane z poprawnym czasem
            mock_save.assert_called()
            call_kwargs = mock_save.call_args[1]
            assert call_kwargs["response_time_ms"] == 500.0


@pytest.mark.asyncio
async def test_token_estimation():
    """Test szacowania tokenów"""
    with patch("httpx.AsyncClient.post") as mock_post, \
            patch("src.services.ai.save_llm_metrics") as mock_save:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {"message": {"content": "Short response"}}
        )

        mock_db = AsyncMock()
        await generate_empathetic_response(
            "Test input message",
            db=mock_db
        )

        # Sprawdź czy tokeny zostały oszacowane
        mock_save.assert_called()
        call_kwargs = mock_save.call_args[1]
        assert call_kwargs["prompt_tokens"] > 0
        assert call_kwargs["completion_tokens"] > 0
        assert call_kwargs["total_tokens"] > 0


def test_metrics_module_availability():
    """Test dostępności modułu metrics"""
    try:
        import src.services.metrics
        # Jeśli import się udał, sprawdź dostępne funkcje
        available_functions = [
            func for func in dir(src.services.metrics)
            if not func.startswith('_')
        ]
        assert len(available_functions) > 0
        print(f"Dostępne funkcje metrics: {available_functions}")
    except ImportError:
        # To jest OK - moduł może nie istnieć
        print("Moduł src.services.metrics nie istnieje - to jest OK")
        assert True
