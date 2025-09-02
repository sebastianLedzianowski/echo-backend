from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc, select
from datetime import datetime, timedelta

from src.database.db import get_db
from src.database.models import User, DiaryEntry, ConversationHistory
from src.services.auth import auth_service

router = APIRouter(prefix="/admin/dashboard", tags=["admin-dashboard"])


@router.get("/overview")
async def get_dashboard_overview(
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Pobiera ogólny przegląd systemu.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    try:
        # Statystyki użytkowników
        result = await db.execute(select(func.count(User.id)))
        total_users = result.scalar()
        
        result = await db.execute(select(func.count(User.id)).filter(User.is_active))
        active_users = result.scalar()
        
        result = await db.execute(select(func.count(User.id)).filter(User.confirmed))
        confirmed_users = result.scalar()
        
        result = await db.execute(select(func.count(User.id)).filter(User.is_admin))
        admin_users = result.scalar()

        # Statystyki dziennika
        result = await db.execute(select(func.count(DiaryEntry.id)))
        total_diary_entries = result.scalar()
        
        result = await db.execute(
            select(func.count(DiaryEntry.id))
            .filter(DiaryEntry.created_at >= datetime.utcnow() - timedelta(days=7))
        )
        recent_diary_entries = result.scalar()

        # Statystyki konwersacji
        result = await db.execute(select(func.count(ConversationHistory.id)))
        total_conversations = result.scalar()
        
        result = await db.execute(
            select(func.count(ConversationHistory.id))
            .filter(ConversationHistory.created_at >= datetime.utcnow() - timedelta(days=7))
        )
        recent_conversations = result.scalar()

        # Statystyki aktywności w ostatnich 24h
        last_24h = datetime.utcnow() - timedelta(hours=24)
        
        result = await db.execute(
            select(func.count(User.id))
            .filter(User.created_at >= last_24h)
        )
        new_users_24h = result.scalar()

        result = await db.execute(
            select(func.count(DiaryEntry.id))
            .filter(DiaryEntry.created_at >= last_24h)
        )
        new_diary_24h = result.scalar()

        result = await db.execute(
            select(func.count(ConversationHistory.id))
            .filter(ConversationHistory.created_at >= last_24h)
        )
        new_conversations_24h = result.scalar()

        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "confirmed": confirmed_users,
                "admins": admin_users,
                "new_24h": new_users_24h
            },
            "diary": {
                "total_entries": total_diary_entries,
                "recent_7_days": recent_diary_entries,
                "new_24h": new_diary_24h
            },
            "conversations": {
                "total": total_conversations,
                "recent_7_days": recent_conversations,
                "new_24h": new_conversations_24h
            },
            "system": {
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Błąd podczas pobierania przeglądu: {str(e)}"
        )


@router.get("/users/stats")
async def get_users_statistics(
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Pobiera szczegółowe statystyki użytkowników.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    try:
        # Użytkownicy według statusu
        result = await db.execute(
            select(
                User.is_active,
                User.confirmed,
                func.count(User.id)
            ).group_by(User.is_active, User.confirmed)
        )
        users_by_status = result.all()

        # Użytkownicy według daty rejestracji (ostatnie 30 dni)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        result = await db.execute(
            select(
                func.date(User.created_at).label('date'),
                func.count(User.id).label('count')
            ).filter(
                User.created_at >= thirty_days_ago
            ).group_by(func.date(User.created_at)).order_by(desc('date'))
        )
        registrations_by_day = result.all()

        # Top użytkownicy według aktywności
        result = await db.execute(
            select(
                User.username,
                User.email,
                func.count(DiaryEntry.id).label('diary_count'),
                func.count(ConversationHistory.id).label('conversation_count')
            ).outerjoin(DiaryEntry).outerjoin(ConversationHistory).group_by(
                User.id, User.username, User.email
            ).order_by(desc('diary_count'), desc('conversation_count')).limit(10)
        )
        top_active_users = result.all()

        return {
            "users_by_status": [
                {
                    "is_active": status[0],
                    "is_confirmed": status[1],
                    "count": status[2]
                }
                for status in users_by_status
            ],
            "registrations_by_day": [
                {
                    "date": str(reg[0]),
                    "count": reg[1]
                }
                for reg in registrations_by_day
            ],
            "top_active_users": [
                {
                    "username": user[0],
                    "email": user[1],
                    "diary_count": user[2],
                    "conversation_count": user[3]
                }
                for user in top_active_users
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Błąd podczas pobierania statystyk użytkowników: {str(e)}"
        )


@router.get("/diary/stats")
async def get_diary_statistics(
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Pobiera statystyki dziennika emocji.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    try:
        # Wpisy według dnia (ostatnie 30 dni)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        result = await db.execute(
            select(
                func.date(DiaryEntry.created_at).label('date'),
                func.count(DiaryEntry.id).label('count')
            ).filter(
                DiaryEntry.created_at >= thirty_days_ago
            ).group_by(func.date(DiaryEntry.created_at)).order_by(desc('date'))
        )
        entries_by_day = result.all()

        # Wpisy według użytkownika
        result = await db.execute(
            select(
                User.username,
                func.count(DiaryEntry.id).label('entry_count')
            ).join(DiaryEntry).group_by(User.id, User.username).order_by(
                desc('entry_count')
            ).limit(20)
        )
        entries_by_user = result.all()

        # Analiza tagów emocji
        all_tags = []
        result = await db.execute(
            select(DiaryEntry.emotion_tags).filter(
                DiaryEntry.emotion_tags.isnot(None)
            )
        )
        entries_with_tags = result.all()

        for entry in entries_with_tags:
            if entry.emotion_tags:
                tags = entry.emotion_tags.split(',') if isinstance(entry.emotion_tags, str) else entry.emotion_tags
                all_tags.extend([tag.strip().lower() for tag in tags if tag.strip()])

        # Liczenie tagów
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Top tagi
        top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "entries_by_day": [
                {
                    "date": str(entry[0]),
                    "count": entry[1]
                }
                for entry in entries_by_day
            ],
            "entries_by_user": [
                {
                    "username": user[0],
                    "entry_count": user[1]
                }
                for user in entries_by_user
            ],
            "emotion_tags": {
                "total_tags": len(all_tags),
                "unique_tags": len(tag_counts),
                "top_tags": [
                    {
                        "tag": tag[0],
                        "count": tag[1]
                    }
                    for tag in top_tags
                ]
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Błąd podczas pobierania statystyk dziennika: {str(e)}"
        )


@router.get("/conversations/stats")
async def get_conversations_statistics(
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Pobiera statystyki konwersacji AI.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    try:
        # Konwersacje według trybu
        result = await db.execute(
            select(
                ConversationHistory.mode,
                func.count(ConversationHistory.id).label('count')
            ).group_by(ConversationHistory.mode)
        )
        conversations_by_mode = result.all()

        # Konwersacje według dnia (ostatnie 30 dni)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        result = await db.execute(
            select(
                func.date(ConversationHistory.created_at).label('date'),
                func.count(ConversationHistory.id).label('count')
            ).filter(
                ConversationHistory.created_at >= thirty_days_ago
            ).group_by(func.date(ConversationHistory.created_at)).order_by(desc('date'))
        )
        conversations_by_day = result.all()

        # Konwersacje według użytkownika
        result = await db.execute(
            select(
                User.username,
                func.count(ConversationHistory.id).label('conversation_count')
            ).join(ConversationHistory).group_by(User.id, User.username).order_by(
                desc('conversation_count')
            ).limit(20)
        )
        conversations_by_user = result.all()

        # Rozkład wiadomości użytkownik vs AI
        result = await db.execute(
            select(func.count(ConversationHistory.id)).filter(
                ConversationHistory.is_user_message
            )
        )
        user_messages = result.scalar()

        result = await db.execute(
            select(func.count(ConversationHistory.id)).filter(
                ConversationHistory.is_user_message.is_(False)
            )
        )
        ai_messages = result.scalar()

        return {
            "conversations_by_mode": [
                {"mode": conv[0], "count": conv[1]}
                for conv in conversations_by_mode
            ],
            "conversations_by_day": [
                {"date": str(conv[0]), "count": conv[1]}
                for conv in conversations_by_day
            ],
            "conversations_by_user": [
                {"username": user[0], "conversation_count": user[1]}
                for user in conversations_by_user
            ],
            "message_distribution": {
                "user_messages": user_messages,
                "ai_messages": ai_messages,
                "total_messages": user_messages + ai_messages
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Błąd podczas pobierania statystyk konwersacji: {str(e)}"
        )


@router.get("/system/health")
async def get_system_health(
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Pobiera status zdrowia systemu (bez Redis).
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    try:
        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "status": "healthy"  # Można dodać realne sprawdzenie połączenia z DB
            },
            "overall_status": "healthy"
        }
        return health_status
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "unhealthy",
            "error": str(e)
        }


@router.get("/all-data")
async def get_all_system_data(
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Pobiera wszystkie dostępne dane systemu w jednym żądaniu (bez Redis).
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    try:
        # Pobierz wszystkie dane równolegle
        overview_data = await get_dashboard_overview(current_user, db)
        users_data = await get_users_statistics(current_user, db)
        diary_data = await get_diary_statistics(current_user, db)
        conversations_data = await get_conversations_statistics(current_user, db)
        health_data = await get_system_health(current_user, db)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overview": overview_data,
            "users": users_data,
            "diary": diary_data,
            "conversations": conversations_data,
            "system_health": health_data
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Błąd podczas pobierania wszystkich danych: {str(e)}"
        )


@router.get("/export")
async def export_system_data(
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db),
        format: str = "json"
):
    """
    Eksportuje wszystkie dane systemu w różnych formatach (bez Redis).
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    try:
        # Pobierz wszystkie dane
        all_data = await get_all_system_data(current_user, db)

        if format.lower() == "csv":
            csv_data = convert_to_csv(all_data)
            return {
                "format": "csv",
                "data": csv_data,
                "filename": f"echo_backend_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        elif format.lower() == "xml":
            xml_data = convert_to_xml(all_data)
            return {
                "format": "xml",
                "data": xml_data,
                "filename": f"echo_backend_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xml"
            }
        else:
            return {
                "format": "json",
                "data": all_data,
                "filename": f"echo_backend_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Błąd podczas eksportu danych: {str(e)}"
        )


def convert_to_csv(data):
    """
    Konwertuje dane do formatu CSV.
    """
    csv_lines = []

    # Dodaj nagłówek
    csv_lines.append("Kategoria,Podkategoria,Wartość,Opis")

    # Overview
    if 'overview' in data:
        overview = data['overview']
        csv_lines.append(f"Użytkownicy,Wszyscy,{overview['users']['total']},Całkowita liczba użytkowników")
        csv_lines.append(f"Użytkownicy,Aktywni,{overview['users']['active']},Aktywni użytkownicy")
        csv_lines.append(f"Użytkownicy,Potwierdzeni,{overview['users']['confirmed']},Potwierdzeni użytkownicy")
        csv_lines.append(f"Użytkownicy,Administratorzy,{overview['users']['admins']},Administratorzy")
        csv_lines.append(f"Użytkownicy,Nowi 24h,{overview['users']['new_24h']},Nowi użytkownicy w ostatnich 24h")
        csv_lines.append(f"Dziennik,Wszystkie wpisy,{overview['diary']['total_entries']},Całkowita liczba wpisów")
        csv_lines.append(f"Dziennik,Ostatnie 7 dni,{overview['diary']['recent_7_days']},Wpisy w ostatnich 7 dniach")
        csv_lines.append(f"Konwersacje,Wszystkie,{overview['conversations']['total']},Całkowita liczba konwersacji")
        csv_lines.append(
            f"Konwersacje,Ostatnie 7 dni,{overview['conversations']['recent_7_days']},Konwersacje w ostatnich 7 dniach")

    # Users stats
    if 'users' in data and 'top_active_users' in data['users']:
        for i, user in enumerate(data['users']['top_active_users']):
            csv_lines.append(
                f"Top Użytkownicy,{i + 1}. {user['username']},{user['diary_count']},Liczba wpisów dziennika")
            csv_lines.append(
                f"Top Użytkownicy,{i + 1}. {user['username']},{user['conversation_count']},Liczba konwersacji")

    # Diary stats
    if 'diary' in data and 'emotion_tags' in data['diary']:
        csv_lines.append(
            f"Tagi Emocji,Wszystkie tagi,{data['diary']['emotion_tags']['total_tags']},Całkowita liczba tagów")
        csv_lines.append(
            f"Tagi Emocji,Unikalne tagi,{data['diary']['emotion_tags']['unique_tags']},Liczba unikalnych tagów")

        for tag in data['diary']['emotion_tags']['top_tags']:
            csv_lines.append(f"Top Tagi,{tag['tag']},{tag['count']},Liczba wystąpień")

    # Conversations stats
    if 'conversations' in data and 'message_distribution' in data['conversations']:
        msg_dist = data['conversations']['message_distribution']
        csv_lines.append(f"Wiadomości,Użytkownicy,{msg_dist['user_messages']},Wiadomości użytkowników")
        csv_lines.append(f"Wiadomości,AI,{msg_dist['ai_messages']},Odpowiedzi AI")
        csv_lines.append(f"Wiadomości,Wszystkie,{msg_dist['total_messages']},Całkowita liczba wiadomości")

    return "\n".join(csv_lines)


def convert_to_xml(data):
    """
    Konwertuje dane do formatu XML.
    """
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_lines.append('<echo_backend_export>')
    xml_lines.append(f'  <timestamp>{data.get("timestamp", "")}</timestamp>')

    # Overview
    if 'overview' in data:
        xml_lines.append('  <overview>')
        overview = data['overview']
        xml_lines.append('    <users>')
        xml_lines.append(f'      <total>{overview["users"]["total"]}</total>')
        xml_lines.append(f'      <active>{overview["users"]["active"]}</active>')
        xml_lines.append(f'      <confirmed>{overview["users"]["confirmed"]}</confirmed>')
        xml_lines.append(f'      <admins>{overview["users"]["admins"]}</admins>')
        xml_lines.append(f'      <new_24h>{overview["users"]["new_24h"]}</new_24h>')
        xml_lines.append('    </users>')
        xml_lines.append('    <diary>')
        xml_lines.append(f'      <total_entries>{overview["diary"]["total_entries"]}</total_entries>')
        xml_lines.append(f'      <recent_7_days>{overview["diary"]["recent_7_days"]}</recent_7_days>')
        xml_lines.append('    </diary>')
        xml_lines.append('    <conversations>')
        xml_lines.append(f'      <total>{overview["conversations"]["total"]}</total>')
        xml_lines.append(f'      <recent_7_days>{overview["conversations"]["recent_7_days"]}</recent_7_days>')
        xml_lines.append('    </conversations>')
        xml_lines.append('  </overview>')

    # Users stats
    if 'users' in data and 'top_active_users' in data['users']:
        xml_lines.append('  <top_users>')
        for user in data['users']['top_active_users']:
            xml_lines.append('    <user>')
            xml_lines.append(f'      <username>{user["username"]}</username>')
            xml_lines.append(f'      <email>{user["email"] or ""}</email>')
            xml_lines.append(f'      <diary_count>{user["diary_count"]}</diary_count>')
            xml_lines.append(f'      <conversation_count>{user["conversation_count"]}</conversation_count>')
            xml_lines.append('    </user>')
        xml_lines.append('  </top_users>')

    # Emotion tags
    if 'diary' in data and 'emotion_tags' in data['diary']:
        xml_lines.append('  <emotion_tags>')
        xml_lines.append(f'    <total>{data["diary"]["emotion_tags"]["total_tags"]}</total>')
        xml_lines.append(f'    <unique>{data["diary"]["emotion_tags"]["unique_tags"]}</unique>')
        xml_lines.append('    <top_tags>')
        for tag in data['diary']['emotion_tags']['top_tags']:
            xml_lines.append(f'      <tag name="{tag["tag"]}" count="{tag["count"]}"/>')
        xml_lines.append('    </top_tags>')
        xml_lines.append('  </emotion_tags>')

    xml_lines.append('</echo_backend_export>')
    return "\n".join(xml_lines)
