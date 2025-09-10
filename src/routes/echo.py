from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.db import get_db
from src.database.models import User
from src.schemas import EchoRequest
from src.services.ai import (
    AIServiceError,
    save_conversation_message,
    get_conversation_history,
    generate_empathetic_response,
    generate_practical_response,
    save_diary_entry,
    test_ollama_connection  # Nowa funkcja diagnostyczna
)
from src.services.metrics import record_conversation, record_diary_entry
from src.services.auth import auth_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/echo", tags=["Echo"])


async def handle_ai_conversation(
        user_id: int, mode: str, text: str, db: AsyncSession
):
    """Obsługuje konwersację z AI z lepszym error handlingiem"""

    # Walidacja długości tekstu
    if len(text.strip()) == 0:
        raise HTTPException(
            status_code=400, detail="Wiadomość nie może być pusta."
        )

    if len(text) > 2000:
        raise HTTPException(
            status_code=400, detail="Tekst jest zbyt długi. Maks. 2000 znaków."
        )

    try:
        # Zapisz wiadomość użytkownika
        await save_conversation_message(
            user_id=user_id,
            mode=mode,
            message=text,
            is_user_message=True,
            db=db
        )
        logger.info(
            f"Zapisano wiadomość użytkownika {user_id} w trybie {mode}"
        )

        # Pobierz historię rozmowy
        conversation_history = await get_conversation_history(
            user_id=user_id, mode=mode, db=db, limit=5
        )
        logger.info(
            f"Pobrano {len(conversation_history)} wiadomości z historii"
        )

        # Generuj odpowiedź AI
        try:
            if mode == "empathetic":
                ai_response = await generate_empathetic_response(
                    text, conversation_history, user_id, "empathetic", db
                )
            elif mode == "practical":
                ai_response = await generate_practical_response(
                    text, conversation_history, user_id, "practical", db
                )
            else:
                raise HTTPException(
                    status_code=400, detail="Nieznany tryb rozmowy."
                )

            logger.info(
                f"Wygenerowano odpowiedź AI dla użytkownika {user_id}"
            )

        except AIServiceError as e:
            logger.error(f"Błąd serwisu AI: {e}")
            # Jeśli to błąd związany z modelem, spróbuj zdiagnozować problem
            if e.error_type == "model_not_found":
                diagnostic = await test_ollama_connection()
                logger.error(f"Diagnostyka Ollama: {diagnostic}")
            raise HTTPException(
                status_code=503,
                detail=f"Usługa AI jest niedostępna: {e.message}"
            )

        # Zapisz odpowiedź AI
        await save_conversation_message(
            user_id=user_id,
            mode=mode,
            message=ai_response,
            is_user_message=False,
            db=db
        )
        logger.info(f"Zapisano odpowiedź AI dla użytkownika {user_id}")

        return {"ai_response": ai_response}

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd w handle_ai_conversation: {e}")
        raise HTTPException(
            status_code=500, detail=f"Wystąpił nieoczekiwany błąd: {str(e)}"
        )


@router.post("/empathetic/send")
async def send_empathetic_message(
        request: EchoRequest,
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Wysyła wiadomość w trybie empatycznym"""
    logger.info(
        f"Otrzymano wiadomość empatyczną od użytkownika {current_user.id}"
    )
    return await handle_ai_conversation(
        current_user.id, "empathetic", request.text, db
    )


@router.post("/practical/send")
async def send_practical_message(
        request: EchoRequest,
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Wysyła wiadomość w trybie praktycznym"""
    logger.info(
        f"Otrzymano wiadomość praktyczną od użytkownika {current_user.id}"
    )
    return await handle_ai_conversation(
        current_user.id, "practical", request.text, db
    )


@router.post("/diary/send")
async def send_diary_message(
        request: EchoRequest,
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Zapisuje wpis do dziennika"""
    try:
        if len(request.text.strip()) == 0:
            raise HTTPException(
                status_code=400, detail="Wpis do dziennika nie może być pusty."
            )

        if len(request.text) > 10000:  # Większy limit dla dziennika
            raise HTTPException(
                status_code=400,
                detail="Wpis do dziennika jest zbyt długi. Maks. 10000 znaków."
            )

        logger.info(
            f"Zapisywanie wpisu do dziennika dla użytkownika {current_user.id}"
        )
        entry = await save_diary_entry(
            user_id=current_user.id, content=request.text, db=db
        )

        # Pobierz zaktualizowaną historię (opcjonalne - może być kosztowne
        # dla dużych dzienników)
        # history = await get_conversation_history(
        #     user_id=current_user.id, mode="diary", db=db, limit=10
        # )

        return {
            "message": "Wpis zapisany pomyślnie",
            "entry": {
                "id": entry.id,
                "content": entry.content,
                "created_at": entry.created_at.isoformat()
            }
            # "updated_history": history  # Wykomentowane dla wydajności
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Błąd zapisywania wpisu do dziennika: {e}")
        raise HTTPException(
            status_code=500, detail="Nie udało się zapisać wpisu do dziennika."
        )


@router.get("/empathetic/history")
async def get_empathetic_history(
        limit: int = 100,  # Dodano parametr limit
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Pobiera historię rozmów empatycznych"""
    try:
        # Walidacja limitu
        if limit > 1000:
            limit = 1000
        elif limit < 1:
            limit = 10

        logger.info(
            f"Pobieranie historii empatycznej dla użytkownika "
            f"{current_user.id} (limit: {limit})"
        )
        history = await get_conversation_history(
            current_user.id, "empathetic", db, limit=limit
        )

        return {
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Błąd pobierania historii empatycznej: {e}")
        raise HTTPException(
            status_code=500, detail="Nie udało się pobrać historii."
        )


@router.get("/practical/history")
async def get_practical_history(
        limit: int = 100,
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Pobiera historię rozmów praktycznych"""
    try:
        if limit > 1000:
            limit = 1000
        elif limit < 1:
            limit = 10

        logger.info(
            f"Pobieranie historii praktycznej dla użytkownika "
            f"{current_user.id} (limit: {limit})"
        )
        history = await get_conversation_history(
            current_user.id, "practical", db, limit=limit
        )

        return {
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Błąd pobierania historii praktycznej: {e}")
        raise HTTPException(
            status_code=500, detail="Nie udało się pobrać historii."
        )


@router.get("/diary/history")
async def get_diary_history(
        limit: int = 100,
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Pobiera historię wpisów do dziennika"""
    try:
        if limit > 1000:
            limit = 1000
        elif limit < 1:
            limit = 10

        logger.info(
            f"Pobieranie historii dziennika dla użytkownika {current_user.id} "
            f"(limit: {limit})"
        )
        history = await get_conversation_history(
            current_user.id, "diary", db, limit=limit
        )

        return {
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Błąd pobierania historii dziennika: {e}")
        raise HTTPException(
            status_code=500, detail="Nie udało się pobrać historii."
        )


@router.get("/diagnostics")
async def get_ai_diagnostics(
        current_user: User = Depends(auth_service.get_current_user)
):
    """Endpoint diagnostyczny dla testowania połączenia z AI
    (tylko dla admina lub debugowania)"""
    try:
        # Opcjonalnie: sprawdź czy użytkownik ma uprawnienia admina
        # if not current_user.is_admin:
        #     raise HTTPException(status_code=403, detail="Brak uprawnień")

        logger.info(
            f"Uruchomiono diagnostykę AI przez użytkownika {current_user.id}"
        )
        diagnostic = await test_ollama_connection()
        return diagnostic
    except Exception as e:
        logger.error(f"Błąd diagnostyki AI: {e}")
        raise HTTPException(
            status_code=500, detail="Nie udało się przeprowadzić diagnostyki."
        )


@router.get("/stats")
async def get_user_stats(
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Pobiera statystyki użytkownika (liczba wiadomości w każdym trybie)"""
    try:
        empathetic_count = len(await get_conversation_history(
            current_user.id, "empathetic", db, limit=10000
        ))
        practical_count = len(await get_conversation_history(
            current_user.id, "practical", db, limit=10000
        ))
        diary_count = len(await get_conversation_history(
            current_user.id, "diary", db, limit=10000
        ))

        return {
            "user_id": current_user.id,
            "empathetic_messages": empathetic_count,
            "practical_messages": practical_count,
            "diary_entries": diary_count,
            "total_messages": empathetic_count + practical_count + diary_count
        }
    except Exception as e:
        logger.error(f"Błąd pobierania statystyk: {e}")
        raise HTTPException(
            status_code=500, detail="Nie udało się pobrać statystyk."
        )
