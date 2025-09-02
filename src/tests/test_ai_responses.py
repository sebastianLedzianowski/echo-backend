import httpx
import pytest
from unittest.mock import patch, AsyncMock
from src.services.ai import AIServiceError

from src.services.ai import (
    generate_empathetic_response,
    generate_practical_response,
    _prepare_conversation_context,
    _prepare_chat_messages
)

# Przykładowa historia rozmowy
sample_history = [
    {"message": "Miałem ciężki dzień.", "is_user_message": True},
    {"message": "Rozumiem, to musiało być trudne.", "is_user_message": False},
]


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


@pytest.mark.asyncio
async def test_prepare_conversation_context():
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


@pytest.mark.asyncio
async def test_prepare_chat_messages():
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


@pytest.mark.asyncio
async def test_empathetic_response_formatting():
    user_input = "Czuję się samotny."
    
    # Mock odpowiedzi AI
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "message": {
                    "content": "Rozumiem, że czujesz się samotny. Czy chcesz mi opowiedzieć więcej o tym, co czujesz?"
                }
            }
        )
        
        response = await generate_empathetic_response(user_input)
        
        # Sprawdzenie czy odpowiedź jest empatyczna
        empathetic_phrases = ["rozumiem", "musi być", "czujesz", "słyszę", "wyobrażam"]
        assert any(phrase in response.lower() for phrase in empathetic_phrases)
        
        # Sprawdzenie czy odpowiedź zawiera pytanie zachęcające do kontynuacji
        assert "?" in response
        
        # Sprawdzenie długości odpowiedzi
        words = response.split()
        assert 10 <= len(words) <= 50  # Odpowiedź nie powinna być ani za krótka, ani za długa


@pytest.mark.asyncio
async def test_practical_response_formatting():
    user_input = "Jak radzić sobie ze stresem?"
    
    # Mock odpowiedzi AI
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "message": {
                    "content": "Oto kilka sposobów na radzenie sobie ze stresem:\n- Uprawiaj regularną aktywność fizyczną\n- Praktykuj techniki oddechowe i medytację\n- Zadbaj o zdrowy sen i odpoczynek"
                }
            }
        )
        
        response = await generate_practical_response(user_input)
        
        # Sprawdzenie czy odpowiedź jest w formie punktów
        lines = response.split("\n")
        bullet_points = [line for line in lines if line.strip().startswith(("-", "•", "*", "1.", "2."))]
        assert len(bullet_points) >= 2  # Powinny być co najmniej 2 punkty
        
        # Sprawdzenie czy każdy punkt ma sensowną długość
        for point in bullet_points:
            words = point.strip().split()
            assert len(words) >= 3  # Każdy punkt powinien mieć co najmniej 3 słowa
        
        # Sprawdzenie całkowitej długości odpowiedzi
        total_words = len(response.split())
        assert 20 <= total_words <= 200  # Odpowiedź powinna być zwięzła, ale kompletna


# ================== TESTY OBSŁUGI BŁĘDÓW ==================
@pytest.mark.asyncio
async def test_empty_response_handling():
    """Test obsługi pustej odpowiedzi od API"""
    with patch('httpx.AsyncClient.post') as mock_post:
            # Symuluj odpowiedź z pustą wiadomością
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: {"message": {"content": "   "}}
            )

            with pytest.raises(AIServiceError) as exc_info:
                await generate_empathetic_response("Test")
            assert exc_info.value.error_type == "empty_response"



@pytest.mark.asyncio
async def test_model_not_found_error():
    """Test obsługi błędu braku modelu"""
    with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=404,
                text="Model not found"
            )

            with pytest.raises(AIServiceError) as exc_info:
                await generate_practical_response("Test")
            assert exc_info.value.error_type == "model_not_found"


@pytest.mark.asyncio
async def test_api_timeout_handling():
    """Test obsługi timeout'u API"""
    with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Connection timeout")

            with pytest.raises(httpx.TimeoutException) as exc_info:
                await generate_empathetic_response("Test")
            assert str(exc_info.value) == "Connection timeout"



@pytest.mark.asyncio
async def test_api_connection_error():
    """Test obsługi błędu połączenia"""
    with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection failed")

            with pytest.raises(httpx.ConnectError) as exc_info:
                await generate_practical_response("Test")
            assert str(exc_info.value) == "Connection failed"



@pytest.mark.asyncio
async def test_retry_mechanism():
    """Test mechanizmu ponownych prób"""
    with patch('httpx.AsyncClient.post') as mock_post:
        # Pierwsze dwa wywołania zwracają błąd, trzecie sukces
        mock_post.side_effect = [
            httpx.TimeoutException("Timeout"),
            httpx.TimeoutException("Timeout"),
            AsyncMock(
                status_code=200,
                json=lambda: {"message": {"content": "Udana odpowiedź"}}
            )
        ]
        
        response = await generate_empathetic_response("Test")
        assert response == "Udana odpowiedź"
        assert mock_post.call_count == 3  # Sprawdź czy były 3 próby


@pytest.mark.asyncio
async def test_invalid_json_response():
    """Test obsługi nieprawidłowej odpowiedzi JSON"""
    with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=200,
                json=lambda: {"invalid": "format"}
            )

            with pytest.raises(AIServiceError) as exc_info:
                await generate_practical_response("Test")
            assert exc_info.value.error_type == "empty_response"


@pytest.mark.asyncio
async def test_server_error_handling():
    """Test obsługi błędu serwera"""
    with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=500,
                text="Internal Server Error"
            )

            with pytest.raises(AIServiceError) as exc_info:
                await generate_empathetic_response("Test")
            assert exc_info.value.error_type == "api_error"


@pytest.mark.asyncio
async def test_rate_limit_handling():
    """Test obsługi przekroczenia limitu zapytań"""
    with patch('httpx.AsyncClient.post') as mock_post:
            mock_post.return_value = AsyncMock(
                status_code=429,
                text="Too Many Requests"
            )

            with pytest.raises(AIServiceError) as exc_info:
                await generate_practical_response("Test")
            assert exc_info.value.error_type == "api_error"


@pytest.mark.asyncio
async def test_malformed_response_handling():
    """Test obsługi nieprawidłowo sformatowanej odpowiedzi"""
    with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = lambda: {"message": None}
            mock_post.return_value = mock_response

            with pytest.raises(AttributeError) as exc_info:
                await generate_empathetic_response("Test")
            assert str(exc_info.value) == "'NoneType' object has no attribute 'get'"



# ================== TESTY HISTORII KONWERSACJI ==================
@pytest.mark.asyncio
async def test_conversation_with_emotional_context():
    """Test konwersacji z kontekstem emocjonalnym"""
    history = [
        {
            "message": "Czuję się dziś bardzo smutny.",
            "is_user_message": True
        },
        {
            "message": "Rozumiem, że jest ci ciężko. Czy chcesz o tym porozmawiać?",
            "is_user_message": False
        },
        {
            "message": "Tak, straciłem pracę.",
            "is_user_message": True
        }
    ]

    # Mock odpowiedzi AI
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "message": {
                    "content": "Rozumiem, że utrata pracy to trudna sytuacja. Czy masz wsparcie bliskich?"
                }
            }
        )

        response = await generate_empathetic_response("Nie wiem, co teraz zrobić.", history)

        # Sprawdzenie czy odpowiedź odnosi się do kontekstu
        assert any(phrase in response.lower() for phrase in [
            "prac",  # praca, pracy
            "trudna sytuacja",
            "rozumiem",
            "wsparcie"
        ])
        # Odpowiedź powinna zawierać pytanie wspierające
        assert "?" in response


@pytest.mark.asyncio
async def test_conversation_with_practical_context():
    """Test konwersacji z kontekstem praktycznym"""
    history = [
        {
            "message": "Chcę zacząć ćwiczyć.",
            "is_user_message": True
        },
        {
            "message": "To świetny pomysł! Jakie ćwiczenia Cię interesują?",
            "is_user_message": False
        },
        {
            "message": "Myślałem o bieganiu.",
            "is_user_message": True
        }
    ]

    # Mock odpowiedzi AI
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "message": {
                    "content": "Oto wskazówki do rozpoczęcia biegania:\n- Kup odpowiednie buty do biegania\n- Zacznij od rozgrzewki\n- Zaplanuj trening"
                }
            }
        )

        response = await generate_practical_response("Od czego powinienem zacząć?", history)

        # Sprawdzenie czy odpowiedź zawiera praktyczne wskazówki związane z bieganiem
        assert any(phrase in response.lower() for phrase in [
            "bieg",  # bieganie, biegi
            "trening",
            "buty",
            "rozgrzewka"
        ])
        # Sprawdzenie formatu punktowego
        assert any(
            line.strip().startswith(("-", "•", "*", "1.", "2."))
            for line in response.split("\n")
        )


@pytest.mark.asyncio
async def test_conversation_with_mixed_context():
    """Test konwersacji z mieszanym kontekstem (emocjonalnym i praktycznym)"""
    history = [
        {
            "message": "Mam problemy ze snem.",
            "is_user_message": True
        },
        {
            "message": "To musi być trudne. Jak długo to trwa?",
            "is_user_message": False
        },
        {
            "message": "Od kilku tygodni, przez stres w pracy.",
            "is_user_message": True
        }
    ]

    # Test odpowiedzi empatycznej
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "message": {
                    "content": "Rozumiem, że problemy ze snem i stres są dla ciebie trudne. Jak sobie z tym radzisz?"
                }
            }
        )
        
        empathetic_response = await generate_empathetic_response(
            "Czuję się przez to coraz gorzej.", history
        )
        assert any(phrase in empathetic_response.lower() for phrase in [
            "sen",
            "stres",
            "rozumiem",
            "trudne"
        ])

    # Test odpowiedzi praktycznej
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "message": {
                    "content": "Oto kilka sposobów na lepszy sen:\n- Ustal stałą rutynę\n- Ogranicz stres przed snem\n- Zadbaj o relaks"
                }
            }
        )
        
        practical_response = await generate_practical_response(
            "Co mogę z tym zrobić?", history
        )
        assert any(phrase in practical_response.lower() for phrase in [
            "sen",
            "stres",
            "relaks",
            "rutyna"
        ])
        # Sprawdzenie formatu punktowego
        assert any(
            line.strip().startswith(("-", "•", "*", "1.", "2."))
            for line in practical_response.split("\n")
        )


@pytest.mark.asyncio
async def test_conversation_with_topic_change():
    """Test konwersacji ze zmianą tematu"""
    history = [
        {
            "message": "Mam problem z kolegą z pracy.",
            "is_user_message": True
        },
        {
            "message": "Rozumiem, że to trudna sytuacja. Co się stało?",
            "is_user_message": False
        },
        {
            "message": "Właściwie, chciałbym porozmawiać o czymś innym.",
            "is_user_message": True
        }
    ]

    # Mock odpowiedzi AI
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "message": {
                    "content": "Rozumiem, że martwisz się o swoje zdrowie. Czy byłeś u lekarza? Jak się czujesz?"
                }
            }
        )

        response = await generate_empathetic_response("Martwię się o swoje zdrowie.", history)

        # Odpowiedź powinna skupić się na nowym temacie
        assert any(phrase in response.lower() for phrase in [
            "zdrowi",  # zdrowie, zdrowia
            "martwi",  # martwisz, martwienie
            "lekarz",
            "samopoczucie"
        ])
        # Sprawdzenie czy stary temat nie jest kontynuowany
        assert "kolega" not in response.lower()
        assert "praca" not in response.lower()


@pytest.mark.asyncio
async def test_conversation_with_long_history():
    """Test konwersacji z długą historią"""
    # Tworzymy długą historię (10 wiadomości)
    history = []
    for i in range(10):
        history.append({
            "message": f"Wiadomość {i+1}",
            "is_user_message": i % 2 == 0
        })

    # Mock odpowiedzi AI
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "message": {
                    "content": "Rozumiem twoją sytuację. Jak mogę ci pomóc?"
                }
            }
        )

        response = await generate_empathetic_response("Nowa wiadomość", history)

        # Sprawdzamy czy odpowiedź jest sensowna mimo długiej historii
        assert isinstance(response, str)
        assert len(response.strip()) > 0
        # Sprawdzamy poprawne zakończenie zdania
        assert response.endswith((".", "!", "?"))


@pytest.mark.asyncio
async def test_conversation_with_short_messages():
    """Test konwersacji z krótkimi wiadomościami"""
    history = [
        {
            "message": "Hej.",
            "is_user_message": True
        },
        {
            "message": "Cześć! Jak mogę ci pomóc?",
            "is_user_message": False
        },
        {
            "message": "Źle.",
            "is_user_message": True
        }
    ]

    # Mock odpowiedzi AI
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = AsyncMock(
            status_code=200,
            json=lambda: {
                "message": {
                    "content": "Chciałbym ci pomóc. Czy możesz mi powiedzieć więcej o tym, co się dzieje?"
                }
            }
        )

        response = await generate_empathetic_response(":(", history)

        # Odpowiedź powinna być rozbudowana mimo krótkich wejść
        assert len(response.split()) >= 10
        # Powinno zawierać pytanie zachęcające do rozwinięcia
        assert "?" in response
        # Sprawdzenie słów zachęcających do rozwinięcia wypowiedzi
        assert any(phrase in response.lower() for phrase in [
            "chcesz",
            "możesz",
            "powiedz",
            "opowiedz"
        ])
