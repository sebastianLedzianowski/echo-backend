import httpx
import logging
import asyncio
import time
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database.models import ConversationHistory, DiaryEntry, LLMMetrics
from src.conf.config import settings
from src.middleware import LLMMetricsContext
from src.services.metrics import record_llm_request, record_conversation, record_diary_entry

logger = logging.getLogger(__name__)


async def save_llm_metrics(
    user_id: Optional[int],
    endpoint: str,
    model_name: str,
    response_time_ms: float,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
    cost_usd: Optional[float] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    db: Optional[AsyncSession] = None
) -> None:
    """Zapisuje metryki LLM do bazy danych"""
    if not db:
        return

    try:
        metrics = LLMMetrics(
            user_id=user_id,
            endpoint=endpoint,
            model_name=model_name,
            response_time_ms=response_time_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            temperature=temperature,
            max_tokens=max_tokens,
            success=success,
            error_message=error_message
        )
        db.add(metrics)
        await db.commit()
        logger.debug(f"Zapisano metryki LLM dla endpointu {endpoint}")
    except Exception as e:
        await db.rollback()
        logger.error(f"Błąd zapisywania metryk LLM: {e}")


def estimate_tokens(text: str) -> int:
    """Szacuje liczbę tokenów w tekście (uproszczone)"""
    # Bardzo proste szacowanie: ~4 znaki na token
    return max(1, len(text) // 4)


class AIServiceError(Exception):
    """Wyjątek dla problemów z serwisem AI."""

    def __init__(self, message: str, error_type: str = "general"):
        self.message = message
        self.error_type = error_type
        super().__init__(self.message)

    def __str__(self):
        return f"{self.error_type}: {self.message}"


# Konfiguracja
OLLAMA_URL = settings.ollama_api_url
OLLAMA_MODEL = settings.ollama_model
REQUEST_TIMEOUT = 120.0
RETRY_COUNT = 3
RETRY_DELAY = 2

SYSTEM_PROMPT_EMPATHETIC = (
    "Jesteś empatycznym, wspierającym rozmówcą. "
    "Twoim zadaniem jest słuchać użytkownika, odzwierciedlać jego emocje "
    "i odpowiadać wspierająco w prostych słowach. "
    "Nie oceniasz, nie krytykujesz, nie udzielasz niechcianych rad. "
    "Odpowiadaj zawsze po polsku. "
    "Zachęcaj do dalszej rozmowy, zadawaj pytania. "
    "Staraj się przedłużać rozmowę. "
)

SYSTEM_PROMPT_PRACTICAL = (
    "Jesteś doradcą udzielającym praktycznych, konkretnych porad. "
    "Odpowiadasz w formie punktów, jasno i zwięźle. "
    "Jeśli masz potrzebę to dopytaj o szczegóły. "
    "Odpowiadaj zawsze po polsku. "
)


def _prepare_conversation_context(
    conversation_history: Optional[List[dict]]
) -> str:
    if not conversation_history:
        return "Brak wcześniejszej historii rozmowy."
    recent_messages = conversation_history[-5:]
    context_parts = []
    for msg in recent_messages:
        role = "Użytkownik" if msg["is_user_message"] else "AI"
        context_parts.append(f"{role}: {msg['message']}")
    return "\n".join(context_parts)


def _prepare_chat_messages(
    prompt: str,
    system_prompt: str,
    conversation_history: Optional[List[dict]] = None
) -> List[dict]:
    """Przygotowuje listę wiadomości dla Chat API"""
    messages = [{"role": "system", "content": system_prompt}]

    # Dodaj kontekst rozmowy jeśli istnieje
    if conversation_history:
        recent_messages = conversation_history[-5:]  # Ostatnie 5 wiadomości
        for msg in recent_messages:
            role = "user" if msg["is_user_message"] else "assistant"
            messages.append({"role": role, "content": msg["message"]})

    # Dodaj aktualny prompt użytkownika
    messages.append({"role": "user", "content": prompt})

    return messages


async def _call_ollama_chat_api(
    prompt: str,
    system_prompt: str,
    mode: str,
    conversation_history: Optional[List[dict]] = None,
    user_id: Optional[int] = None,
    endpoint: str = "unknown",
    db: Optional[AsyncSession] = None
) -> str:
    """Główna funkcja komunikacji z Ollama Chat API"""
    last_error = None
    start_time = time.time()
    
    # Use metrics context
    with LLMMetricsContext(model=OLLAMA_MODEL, endpoint=endpoint) as metrics_ctx:
        for attempt in range(1, RETRY_COUNT + 1):
            try:
                messages = _prepare_chat_messages(
                    prompt, system_prompt, conversation_history
                )

                payload = {
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "stop": [
                            "<|start_header_id|>",
                            "<|end_header_id|>",
                            "<|eot_id|>"
                        ],
                        "temperature": 0.1
                    }
                }

                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    response = await client.post(
                        f"{OLLAMA_URL}/api/chat", json=payload
                    )

                if response.status_code == 200:
                    result = response.json()
                    message = result.get("message", {})
                    ai_response = message.get("content", "").strip()

                    if not ai_response or len(ai_response.split()) < 1:
                        raise AIServiceError(
                            "Pusta lub zbyt krótka odpowiedź", "empty_response"
                        )

                    # Oblicz czasy i tokeny
                    response_time_ms = (time.time() - start_time) * 1000
                    prompt_text = " ".join([msg["content"] for msg in messages])
                    prompt_tokens = estimate_tokens(prompt_text)
                    completion_tokens = estimate_tokens(ai_response)
                    total_tokens = prompt_tokens + completion_tokens

                    # Set metrics context data
                    metrics_ctx.set_tokens(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens
                    )

                    # Zapisz metryki do bazy danych
                    await save_llm_metrics(
                        user_id=user_id,
                        endpoint=endpoint,
                        model_name=OLLAMA_MODEL,
                        response_time_ms=response_time_ms,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        temperature=0.1,
                        success=True,
                        db=db
                    )

                    return ai_response

                elif response.status_code == 404:
                    raise AIServiceError(
                        f"Model {OLLAMA_MODEL} nie został znaleziony.",
                        "model_not_found"
                    )

                else:
                    try:
                        error_data = response.json()
                        error_text = error_data.get("error", response.text)
                    except Exception:
                        error_text = response.text

                    raise AIServiceError(
                        f"Błąd API ({response.status_code}): {error_text}",
                        "api_error"
                    )

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                logger.warning(
                    f"Próba {attempt}/{RETRY_COUNT} nieudana "
                    f"({type(e).__name__}). Ponawiam za {RETRY_DELAY}s..."
                )
                if attempt < RETRY_COUNT:
                    await asyncio.sleep(RETRY_DELAY)

            except AIServiceError as e:
                logger.error(f"{str(e)}")
                # Zapisz błąd jako metrykę
                response_time_ms = (time.time() - start_time) * 1000
                await save_llm_metrics(
                    user_id=user_id,
                    endpoint=endpoint,
                    model_name=OLLAMA_MODEL,
                    response_time_ms=response_time_ms,
                    success=False,
                    error_message=str(e),
                    db=db
                )
                raise

            except Exception as e:
                last_error = e
                logger.error(f"Nieoczekiwany błąd: {e}")
                # Zapisz błąd jako metrykę
                response_time_ms = (time.time() - start_time) * 1000
                await save_llm_metrics(
                    user_id=user_id,
                    endpoint=endpoint,
                    model_name=OLLAMA_MODEL,
                    response_time_ms=response_time_ms,
                    success=False,
                    error_message=str(e),
                    db=db
                )

        logger.error(f"Nie udało się po {RETRY_COUNT} próbach: {last_error}")
        # Zapisz końcowy błąd
        response_time_ms = (time.time() - start_time) * 1000
        await save_llm_metrics(
            user_id=user_id,
            endpoint=endpoint,
            model_name=OLLAMA_MODEL,
            response_time_ms=response_time_ms,
            success=False,
            error_message=str(last_error),
            db=db
        )
        raise last_error


async def generate_empathetic_response(
    user_text: str,
    conversation_history: Optional[List[dict]] = None,
    user_id: Optional[int] = None,
    endpoint: str = "empathetic",
    db: Optional[AsyncSession] = None
) -> str:
    """Generuje empatyczną odpowiedź"""
    return await _call_ollama_chat_api(
        user_text,
        SYSTEM_PROMPT_EMPATHETIC,
        "empathetic",
        conversation_history,
        user_id,
        endpoint,
        db
    )


async def generate_practical_response(
    user_text: str,
    conversation_history: Optional[List[dict]] = None,
    user_id: Optional[int] = None,
    endpoint: str = "practical",
    db: Optional[AsyncSession] = None
) -> str:
    """Generuje praktyczną odpowiedź"""
    return await _call_ollama_chat_api(
        user_text,
        SYSTEM_PROMPT_PRACTICAL,
        "practical",
        conversation_history,
        user_id,
        endpoint,
        db
    )


async def _call_ollama_generate_api(
    prompt: str,
    system_prompt: str = "",
    user_id: Optional[int] = None,
    endpoint: str = "generate",
    db: Optional[AsyncSession] = None
) -> str:
    """
    Funkcja komunikacji z Ollama Generate API (bez streamu)
    Używana dla długich analiz jak testy psychologiczne
    """
    last_error = None
    start_time = time.time()

    # Łączymy system prompt z głównym promptem
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

    for attempt in range(1, RETRY_COUNT + 1):
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "top_k": 40,
                    "stop": [
                        "<|start_header_id|>",
                        "<|end_header_id|>",
                        "<|eot_id|>"
                    ]
                }
            }

            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{OLLAMA_URL}/api/generate", json=payload
                )

            if response.status_code == 200:
                result = response.json()
                ai_response = result.get("response", "").strip()

                if not ai_response:
                    logger.warning(
                        f"Pusta odpowiedź z Ollama (próba {attempt})"
                    )
                    last_error = AIServiceError(
                        "empty_response", "Otrzymano pustą odpowiedź"
                    )
                    continue

                # Oblicz czasy i tokeny
                response_time_ms = (time.time() - start_time) * 1000
                prompt_tokens = estimate_tokens(full_prompt)
                completion_tokens = estimate_tokens(ai_response)
                total_tokens = prompt_tokens + completion_tokens

                # Zapisz metryki
                await save_llm_metrics(
                    user_id=user_id,
                    endpoint=endpoint,
                    model_name=OLLAMA_MODEL,
                    response_time_ms=response_time_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    temperature=0.1,
                    success=True,
                    db=db
                )

                logger.info(
                    f"Otrzymano odpowiedź z Ollama Generate API (próba {attempt})"
                )
                return ai_response

            else:
                error_detail = f"HTTP {response.status_code}"
                try:
                    error_body = response.json()
                    if "error" in error_body:
                        error_detail += f": {error_body['error']}"
                except Exception:
                    error_detail += f": {response.text[:200]}"

                logger.error(
                    f"Błąd Ollama Generate API (próba {attempt}): "
                    f"{error_detail}"
                )

                if response.status_code == 404:
                    last_error = AIServiceError(
                        "model_not_found",
                        f"Model {OLLAMA_MODEL} nie został znaleziony"
                    )
                else:
                    last_error = AIServiceError(
                        "api_error", f"Błąd API: {error_detail}"
                    )

        except httpx.TimeoutException:
            logger.error(f"Timeout Ollama Generate API (próba {attempt})")
            last_error = AIServiceError(
                "timeout", "Przekroczono limit czasu odpowiedzi"
            )
        except httpx.RequestError as e:
            logger.error(
                f"Błąd połączenia z Ollama Generate API (próba {attempt}): {e}"
            )
            last_error = AIServiceError(
                "connection_error", f"Błąd połączenia: {str(e)}"
            )
        except Exception as e:
            logger.error(
                f"Nieoczekiwany błąd Ollama Generate API (próba {attempt}): "
                f"{e}"
            )
            last_error = AIServiceError(
                "unexpected_error", f"Nieoczekiwany błąd: {str(e)}"
            )

        if attempt < RETRY_COUNT:
            await asyncio.sleep(RETRY_DELAY)

    # Wszystkie próby nieudane
    if last_error:
        raise last_error
    else:
        raise AIServiceError(
            "unknown_error", "Nieznany błąd podczas komunikacji z AI"
        )


async def get_ai_response(
    prompt: str,
    mode: str = "empathetic",
    user_id: Optional[int] = None,
    endpoint: str = "ai_response",
    db: Optional[AsyncSession] = None
) -> str:
    """Generuje odpowiedź AI na podstawie promptu i trybu"""
    if mode == "empathetic":
        return await _call_ollama_chat_api(
            prompt,
            SYSTEM_PROMPT_EMPATHETIC,
            mode,
            user_id=user_id,
            endpoint=endpoint,
            db=db
        )
    elif mode == "practical":
        return await _call_ollama_chat_api(
            prompt,
            SYSTEM_PROMPT_PRACTICAL,
            mode,
            user_id=user_id,
            endpoint=endpoint,
            db=db
        )
    else:
        return await _call_ollama_generate_api(
            prompt,
            SYSTEM_PROMPT_EMPATHETIC,
            user_id=user_id,
            endpoint=endpoint,
            db=db
        )


async def get_ai_analysis_response(
    prompt: str,
    user_id: Optional[int] = None,
    endpoint: str = "ai_analysis",
    db: Optional[AsyncSession] = None
) -> str:
    """
    Generuje szczegółową analizę AI używając /api/chat
    Specjalnie dla testów psychologicznych i długich analiz
    """
    # System prompt dla analiz psychologicznych
    system_prompt = """Jesteś doświadczonym psychologiem klinicznym z 
    wieloletnim doświadczeniem w diagnostyce i analizie testów psychologicznych.
    Twoim zadaniem jest przeprowadzenie szczegółowej, profesjonalnej analizy
    wyników testów przesiewowych.

    ZASADY PROFESJONALNE:
    - Używaj empatycznego, ale profesjonalnego tonu
    - Podkreślaj, że test ma charakter PRZESIEWOWY, nie diagnostyczny
    - Zawsze zalecaj konsultację ze specjalistą (psycholog/psychiatra)
    - Bądź konkretny w swoich obserwacjach i rekomendacjach
    - Unikaj stawiania ostatecznych diagnoz
    - Skup się na praktycznych strategiach wsparcia
    - W przypadku myśli samobójczych podkreśl pilną potrzebę pomocy

    STYL KOMUNIKACJI:
    - Jasny, zrozumiały język
    - Wspierający, ale nie bagatelizujący
    - Konkretne rekomendacje
    - Podkreślanie nadziei i możliwości poprawy
    - Zawsze kończ pozytywnym akcentem"""

    return await _call_ollama_chat_api(
        prompt,
        system_prompt,
        "analysis",
        user_id=user_id,
        endpoint=endpoint,
        db=db
    )


async def save_conversation_message(
    user_id: int,
    mode: str,
    message: str,
    is_user_message: bool,
    db: AsyncSession
) -> None:
    """Zapisuje wiadomość do historii konwersacji"""
    try:
        entry = ConversationHistory(
            user_id=user_id,
            mode=mode,
            message=message,
            is_user_message=is_user_message
        )
        db.add(entry)
        await db.commit()
        
        # Record conversation metrics
        if is_user_message:
            record_conversation(mode=mode, user_type="authenticated")
        
        logger.info(
            f"Zapisano wiadomość dla użytkownika {user_id} w trybie {mode}"
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Błąd zapisywania wiadomości: {e}")
        raise


async def save_diary_entry(
    user_id: int,
    content: str,
    title: Optional[str] = None,
    db: Optional[AsyncSession] = None
):
    """Zapisuje wpis do dziennika"""
    entry = DiaryEntry(user_id=user_id, title=title, content=content)
    if db:
        try:
            db.add(entry)
            await db.commit()
            await db.refresh(entry)
            
            # Record diary entry metrics
            record_diary_entry()
            
            logger.info(
                f"Zapisano wpis do dziennika dla użytkownika {user_id}"
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"Błąd zapisywania wpisu do dziennika: {e}")
            raise
    return entry


async def get_conversation_history(
    user_id: int,
    mode: str,
    db: AsyncSession,
    limit: int = 20
):
    """Pobiera historię konwersacji dla użytkownika"""
    try:
        stmt = select(ConversationHistory).where(
            ConversationHistory.user_id == user_id,
            ConversationHistory.mode == mode
        ).order_by(ConversationHistory.created_at.desc()).limit(limit)

        result = await db.execute(stmt)
        entries = result.scalars().all()

        history = [
            {
                "message": e.message,
                "is_user_message": e.is_user_message,
                "created_at": e.created_at.isoformat()
            }
            for e in entries
        ]

        # Zwracamy w chronologicznej kolejności (najstarsze pierwsze)
        return sorted(history, key=lambda x: x["created_at"])

    except Exception as e:
        logger.error(f"Błąd pobierania historii konwersacji: {e}")
        return []


# Funkcja diagnostyczna
async def test_ollama_connection() -> dict:
    """Testuje połączenie z Ollama i zwraca informacje diagnostyczne"""
    result = {
        "ollama_url": OLLAMA_URL,
        "model": OLLAMA_MODEL,
        "chat_api_working": False,
        "generate_api_working": False,
        "model_loaded": False,
        "chat_response": "",
        "generate_response": "",
        "errors": []
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test połączenia z Ollama
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                result["model_loaded"] = OLLAMA_MODEL in model_names

                if not result["model_loaded"]:
                    result["errors"].append(
                        f"Model {OLLAMA_MODEL} nie jest załadowany. "
                        f"Dostępne modele: {model_names}"
                    )

            # Test Chat API z różnymi opcjami
            try:
                # Test 1: Chat API z właściwym formatem
                chat_payload = {
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {
                            "role": "user", 
                            "content": "Odpowiedz krótko: czy mnie słyszysz?"
                        }
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "stop": ["<|im_end|>"],
                        "num_predict": 50
                    },
                    "raw": False
                }
                chat_response = await client.post(
                    f"{OLLAMA_URL}/api/chat", json=chat_payload
                )
                result["chat_api_working"] = chat_response.status_code == 200
                if chat_response.status_code == 200:
                    chat_result = chat_response.json()
                    result["chat_response"] = chat_result.get("message", {}).get(
                        "content", ""
                    )
                else:
                    result["errors"].append(
                        f"Chat API error: {chat_response.status_code} - "
                        f"{chat_response.text}"
                    )
            except Exception as e:
                result["errors"].append(f"Chat API error: {e}")

            # Test Generate API
            try:
                generate_payload = {
                    "model": OLLAMA_MODEL,
                    "prompt": (
                        "<|im_start|>user\nOdpowiedz krótko: czy mnie słyszysz?"
                        "<|im_end|>\n<|im_start|>assistant\n"
                    ),
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "stop": ["<|im_end|>"],
                        "num_predict": 50
                    },
                    "raw": True
                }
                generate_response = await client.post(
                    f"{OLLAMA_URL}/api/generate", json=generate_payload
                )
                result["generate_api_working"] = generate_response.status_code == 200
                if generate_response.status_code == 200:
                    generate_result = generate_response.json()
                    result["generate_response"] = generate_result.get("response", "")
                else:
                    result["errors"].append(
                        f"Generate API error: {generate_response.status_code} - "
                        f"{generate_response.text}"
                    )
            except Exception as e:
                result["errors"].append(f"Generate API error: {e}")

    except Exception as e:
        result["errors"].append(f"Connection error: {e}")

    return result
