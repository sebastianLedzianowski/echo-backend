import os
import httpx
import logging
import asyncio
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database.models import ConversationHistory, DiaryEntry

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Wyjątek dla problemów z serwisem AI."""

    def __init__(self, message: str, error_type: str = "general"):
        self.message = message
        self.error_type = error_type
        super().__init__(self.message)

    def __str__(self):
        return f"{self.error_type}: {self.message}"


# Konfiguracja
OLLAMA_URL = os.getenv("OLLAMA_API_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
REQUEST_TIMEOUT = 120.0
RETRY_COUNT = 3
RETRY_DELAY = 2

SYSTEM_PROMPT_EMPATHETIC = (
    "Jesteś empatycznym, wspierającym rozmówcą. "
    "Twoim zadaniem jest słuchać użytkownika, odzwierciedlać jego emocje "
    "i odpowiadać wspierająco w prostych słowach. "
    "Nie oceniasz, nie krytykujesz, nie udzielasz niechcianych rad. "
    "Odpowiadaj zawsze po polsku. "
    "Zachęcaj do dalszej rozmowy, zadawaj pytania. Staraj się przedłużać rozmowę. "
)

SYSTEM_PROMPT_PRACTICAL = (
    "Jesteś doradcą udzielającym praktycznych, konkretnych porad. "
    "Odpowiadasz w formie punktów, jasno i zwięźle. "
    "Jeśli masz potrzebę to dopytaj o szczegóły. "
    "Odpowiadaj zawsze po polsku. "
)


def _prepare_conversation_context(conversation_history: Optional[List[dict]]) -> str:
    if not conversation_history:
        return "Brak wcześniejszej historii rozmowy."
    recent_messages = conversation_history[-5:]
    context_parts = []
    for msg in recent_messages:
        role = "Użytkownik" if msg["is_user_message"] else "AI"
        context_parts.append(f"{role}: {msg['message']}")
    return "\n".join(context_parts)


def _prepare_chat_messages(prompt: str, system_prompt: str, conversation_history: Optional[List[dict]] = None) -> List[
    dict]:
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


async def _call_ollama_chat_api(prompt: str, system_prompt: str, mode: str,
                                conversation_history: Optional[List[dict]] = None) -> str:
    """Główna funkcja komunikacji z Ollama Chat API"""
    last_error = None
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            messages = _prepare_chat_messages(prompt, system_prompt, conversation_history)

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
                response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)

            if response.status_code == 200:
                result = response.json()
                message = result.get("message", {})
                ai_response = message.get("content", "").strip()

                if not ai_response or len(ai_response.split()) < 1:
                    raise AIServiceError("Pusta lub zbyt krótka odpowiedź", "empty_response")

                return ai_response

            elif response.status_code == 404:
                raise AIServiceError(f"Model {OLLAMA_MODEL} nie został znaleziony.", "model_not_found")

            else:
                try:
                    error_data = response.json()
                    error_text = error_data.get("error", response.text)
                except:
                    error_text = response.text

                raise AIServiceError(f"Błąd API ({response.status_code}): {error_text}", "api_error")

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_error = e
            logger.warning(
                f"Próba {attempt}/{RETRY_COUNT} nieudana ({type(e).__name__}). Ponawiam za {RETRY_DELAY}s..."
            )
            if attempt < RETRY_COUNT:
                await asyncio.sleep(RETRY_DELAY)

        except AIServiceError as e:
            logger.error(f"{str(e)}")
            # ⬇️ Tutaj zwracamy komunikat dla użytkownika
            return "⚠️ Wystąpił problem z generowaniem odpowiedzi. Spróbuj ponownie za chwilę."

        except Exception as e:
            last_error = e
            logger.error(f"Nieoczekiwany błąd: {e}")

    logger.error(f"Nie udało się po {RETRY_COUNT} próbach: {last_error}")
    return "⚠️ Serwis jest chwilowo niedostępny. Spróbuj ponownie za kilka minut."


async def generate_empathetic_response(user_text: str, conversation_history: Optional[List[dict]] = None) -> str:
    """Generuje empatyczną odpowiedź"""
    try:
        return await _call_ollama_chat_api(user_text, SYSTEM_PROMPT_EMPATHETIC, "empathetic", conversation_history)
    except Exception as e:
        logger.error(f"Błąd w generate_empathetic_response: {e}")
        return "⚠️ Wystąpił problem z wygenerowaniem odpowiedzi. Spróbuj ponownie za chwilę."


async def generate_practical_response(user_text: str, conversation_history: Optional[List[dict]] = None) -> str:
    """Generuje praktyczną odpowiedź"""
    try:
        return await _call_ollama_chat_api(user_text, SYSTEM_PROMPT_PRACTICAL, "practical", conversation_history)
    except Exception as e:
        logger.error(f"Błąd w generate_practical_response: {e}")
        return "⚠️ Wystąpił problem z wygenerowaniem odpowiedzi. Spróbuj ponownie za chwilę."


async def save_conversation_message(user_id: int, mode: str, message: str, is_user_message: bool,
                                    db: AsyncSession) -> None:
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
        logger.info(f"Zapisano wiadomość dla użytkownika {user_id} w trybie {mode}")
    except Exception as e:
        await db.rollback()
        logger.error(f"Błąd zapisywania wiadomości: {e}")
        raise


async def save_diary_entry(user_id: int, content: str, title: Optional[str] = None, db: Optional[AsyncSession] = None):
    """Zapisuje wpis do dziennika"""
    entry = DiaryEntry(user_id=user_id, title=title, content=content)
    if db:
        try:
            db.add(entry)
            await db.commit()
            await db.refresh(entry)
            logger.info(f"Zapisano wpis do dziennika dla użytkownika {user_id}")
        except Exception as e:
            await db.rollback()
            logger.error(f"Błąd zapisywania wpisu do dziennika: {e}")
            raise
    return entry


async def get_conversation_history(user_id: int, mode: str, db: AsyncSession, limit: int = 20):
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
                    result["errors"].append(f"Model {OLLAMA_MODEL} nie jest załadowany. Dostępne modele: {model_names}")

            # Test Chat API z różnymi opcjami
            try:
                # Test 1: Chat API z właściwym formatem
                chat_payload = {
                    "model": OLLAMA_MODEL,
                    "messages": [{"role": "user", "content": "Odpowiedz krótko: czy mnie słyszysz?"}],
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "stop": ["<|im_end|>"],
                        "num_predict": 50
                    },
                    "raw": False
                }
                chat_response = await client.post(f"{OLLAMA_URL}/api/chat", json=chat_payload)
                result["chat_api_working"] = chat_response.status_code == 200
                if chat_response.status_code == 200:
                    chat_result = chat_response.json()
                    result["chat_response"] = chat_result.get("message", {}).get("content", "")
                else:
                    result["errors"].append(f"Chat API error: {chat_response.status_code} - {chat_response.text}")
            except Exception as e:
                result["errors"].append(f"Chat API error: {e}")

            # Test Generate API
            try:
                generate_payload = {
                    "model": OLLAMA_MODEL,
                    "prompt": "<|im_start|>user\nOdpowiedz krótko: czy mnie słyszysz?<|im_end|>\n<|im_start|>assistant\n",
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "stop": ["<|im_end|>"],
                        "num_predict": 50
                    },
                    "raw": True
                }
                generate_response = await client.post(f"{OLLAMA_URL}/api/generate", json=generate_payload)
                result["generate_api_working"] = generate_response.status_code == 200
                if generate_response.status_code == 200:
                    generate_result = generate_response.json()
                    result["generate_response"] = generate_result.get("response", "")
                else:
                    result["errors"].append(
                        f"Generate API error: {generate_response.status_code} - {generate_response.text}")
            except Exception as e:
                result["errors"].append(f"Generate API error: {e}")

    except Exception as e:
        result["errors"].append(f"Connection error: {e}")

    return result
