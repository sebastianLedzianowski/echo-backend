from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc, select
from datetime import datetime, timedelta

from src.database.db import get_db
from src.database.models import User, DiaryEntry, ConversationHistory, ApiHit, SystemMetrics, PsychologicalTest
from src.services.auth import auth_service

router = APIRouter(prefix="/admin/stats", tags=["admin-stats"])


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

        # Statystyki API hits
        result = await db.execute(select(func.count(ApiHit.id)))
        total_api_hits = result.scalar()
        
        result = await db.execute(
            select(func.count(ApiHit.id))
            .filter(ApiHit.created_at >= datetime.utcnow() - timedelta(hours=24))
        )
        api_hits_24h = result.scalar()

        # Statystyki testów psychologicznych
        result = await db.execute(select(func.count(PsychologicalTest.id)))
        total_tests = result.scalar()
        
        result = await db.execute(
            select(func.count(PsychologicalTest.id))
            .filter(PsychologicalTest.created_at >= datetime.utcnow() - timedelta(days=7))
        )
        recent_tests = result.scalar()

        # Średni czas odpowiedzi w ostatnich 24h
        result = await db.execute(
            select(func.avg(ApiHit.response_time_ms))
            .filter(
                ApiHit.created_at >= datetime.utcnow() - timedelta(hours=24),
                ApiHit.response_time_ms.isnot(None)
            )
        )
        avg_response_time_24h = result.scalar() or 0

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
            "api": {
                "total_hits": total_api_hits,
                "hits_24h": api_hits_24h,
                "avg_response_time_24h_ms": round(avg_response_time_24h, 2)
            },
            "tests": {
                "total": total_tests,
                "recent_7_days": recent_tests
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
        api_data = await get_api_statistics(current_user, db)
        performance_data = await get_performance_statistics(current_user, db)
        tests_data = await get_tests_statistics(current_user, db)
        health_data = await get_system_health(current_user, db)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "overview": overview_data,
            "users": users_data,
            "diary": diary_data,
            "conversations": conversations_data,
            "api": api_data,
            "performance": performance_data,
            "tests": tests_data,
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
        csv_lines.append(f"API,Wszystkie uderzenia,{overview['api']['total_hits']},Całkowita liczba uderzeń API")
        csv_lines.append(f"API,Uderzenia 24h,{overview['api']['hits_24h']},Uderzenia API w ostatnich 24h")
        csv_lines.append(f"API,Średni czas odpowiedzi,{overview['api']['avg_response_time_24h_ms']},Średni czas odpowiedzi w ms")
        csv_lines.append(f"Testy,Wszystkie,{overview['tests']['total']},Całkowita liczba testów")
        csv_lines.append(f"Testy,Ostatnie 7 dni,{overview['tests']['recent_7_days']},Testy w ostatnich 7 dniach")

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

    # API stats
    if 'api' in data and 'error_metrics' in data['api']:
        error_metrics = data['api']['error_metrics']
        csv_lines.append(f"API,Błędy,{error_metrics['error_count']},Liczba błędów")
        csv_lines.append(f"API,Wszystkie żądania,{error_metrics['total_requests']},Całkowita liczba żądań")
        csv_lines.append(f"API,Procent błędów,{error_metrics['error_rate_percent']},Procent błędów")

    # Performance stats
    if 'performance' in data and 'response_time_percentiles' in data['performance']:
        percentiles = data['performance']['response_time_percentiles']
        csv_lines.append(f"Wydajność,P95,{percentiles['p95_ms']},95 percentyl czasu odpowiedzi")
        csv_lines.append(f"Wydajność,P99,{percentiles['p99_ms']},99 percentyl czasu odpowiedzi")

    # Tests stats
    if 'tests' in data and 'tests_by_type' in data['tests']:
        for test in data['tests']['tests_by_type']:
            csv_lines.append(f"Testy,{test['test_type']},{test['count']},Liczba testów {test['test_type']}")
            csv_lines.append(f"Testy,{test['test_type']} średni wynik,{test['avg_score']},Średni wynik {test['test_type']}")

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
        xml_lines.append('    <api>')
        xml_lines.append(f'      <total_hits>{overview["api"]["total_hits"]}</total_hits>')
        xml_lines.append(f'      <hits_24h>{overview["api"]["hits_24h"]}</hits_24h>')
        xml_lines.append(f'      <avg_response_time_24h_ms>{overview["api"]["avg_response_time_24h_ms"]}</avg_response_time_24h_ms>')
        xml_lines.append('    </api>')
        xml_lines.append('    <tests>')
        xml_lines.append(f'      <total>{overview["tests"]["total"]}</total>')
        xml_lines.append(f'      <recent_7_days>{overview["tests"]["recent_7_days"]}</recent_7_days>')
        xml_lines.append('    </tests>')
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


@router.get("/api/stats")
async def get_api_statistics(
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Pobiera szczegółowe statystyki API i czasów odpowiedzi.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    try:
        # Statystyki według endpointów (ostatnie 30 dni)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        result = await db.execute(
            select(
                ApiHit.endpoint,
                ApiHit.method,
                func.count(ApiHit.id).label('count'),
                func.avg(ApiHit.response_time_ms).label('avg_response_time'),
                func.max(ApiHit.response_time_ms).label('max_response_time'),
                func.min(ApiHit.response_time_ms).label('min_response_time')
            ).filter(
                ApiHit.created_at >= thirty_days_ago
            ).group_by(ApiHit.endpoint, ApiHit.method).order_by(desc('count'))
        )
        endpoint_stats = result.all()

        # Statystyki według statusów odpowiedzi
        result = await db.execute(
            select(
                ApiHit.response_status,
                func.count(ApiHit.id).label('count')
            ).filter(
                ApiHit.created_at >= thirty_days_ago
            ).group_by(ApiHit.response_status).order_by(desc('count'))
        )
        status_stats = result.all()

        # Statystyki według dnia (ostatnie 30 dni)
        result = await db.execute(
            select(
                func.date(ApiHit.created_at).label('date'),
                func.count(ApiHit.id).label('count'),
                func.avg(ApiHit.response_time_ms).label('avg_response_time')
            ).filter(
                ApiHit.created_at >= thirty_days_ago
            ).group_by(func.date(ApiHit.created_at)).order_by(desc('date'))
        )
        daily_stats = result.all()

        # Top użytkownicy według aktywności API
        result = await db.execute(
            select(
                User.username,
                func.count(ApiHit.id).label('api_calls'),
                func.avg(ApiHit.response_time_ms).label('avg_response_time')
            ).join(ApiHit).filter(
                ApiHit.created_at >= thirty_days_ago
            ).group_by(User.id, User.username).order_by(desc('api_calls')).limit(20)
        )
        top_api_users = result.all()

        # Statystyki błędów (4xx, 5xx)
        result = await db.execute(
            select(func.count(ApiHit.id)).filter(
                ApiHit.response_status >= 400,
                ApiHit.created_at >= thirty_days_ago
            )
        )
        error_count = result.scalar()

        result = await db.execute(
            select(func.count(ApiHit.id)).filter(
                ApiHit.created_at >= thirty_days_ago
            )
        )
        total_requests = result.scalar()

        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0

        return {
            "endpoint_stats": [
                {
                    "endpoint": stat[0],
                    "method": stat[1],
                    "count": stat[2],
                    "avg_response_time_ms": round(stat[3] or 0, 2),
                    "max_response_time_ms": round(stat[4] or 0, 2),
                    "min_response_time_ms": round(stat[5] or 0, 2)
                }
                for stat in endpoint_stats
            ],
            "status_stats": [
                {
                    "status_code": stat[0],
                    "count": stat[1]
                }
                for stat in status_stats
            ],
            "daily_stats": [
                {
                    "date": str(stat[0]),
                    "count": stat[1],
                    "avg_response_time_ms": round(stat[2] or 0, 2)
                }
                for stat in daily_stats
            ],
            "top_api_users": [
                {
                    "username": user[0],
                    "api_calls": user[1],
                    "avg_response_time_ms": round(user[2] or 0, 2)
                }
                for user in top_api_users
            ],
            "error_metrics": {
                "error_count": error_count,
                "total_requests": total_requests,
                "error_rate_percent": round(error_rate, 2)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Błąd podczas pobierania statystyk API: {str(e)}"
        )


@router.get("/performance/stats")
async def get_performance_statistics(
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Pobiera statystyki wydajności systemu.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    try:
        # Średnie czasy odpowiedzi według godzin (ostatnie 24h)
        last_24h = datetime.utcnow() - timedelta(hours=24)
        result = await db.execute(
            select(
                func.extract('hour', ApiHit.created_at).label('hour'),
                func.avg(ApiHit.response_time_ms).label('avg_response_time'),
                func.count(ApiHit.id).label('request_count')
            ).filter(
                ApiHit.created_at >= last_24h,
                ApiHit.response_time_ms.isnot(None)
            ).group_by(func.extract('hour', ApiHit.created_at)).order_by('hour')
        )
        hourly_performance = result.all()

        # Najwolniejsze endpointy (ostatnie 7 dni)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        result = await db.execute(
            select(
                ApiHit.endpoint,
                ApiHit.method,
                func.avg(ApiHit.response_time_ms).label('avg_response_time'),
                func.count(ApiHit.id).label('request_count')
            ).filter(
                ApiHit.created_at >= seven_days_ago,
                ApiHit.response_time_ms.isnot(None)
            ).group_by(ApiHit.endpoint, ApiHit.method).order_by(desc('avg_response_time')).limit(10)
        )
        slowest_endpoints = result.all()

        # Statystyki według dni tygodnia
        result = await db.execute(
            select(
                func.extract('dow', ApiHit.created_at).label('day_of_week'),
                func.avg(ApiHit.response_time_ms).label('avg_response_time'),
                func.count(ApiHit.id).label('request_count')
            ).filter(
                ApiHit.created_at >= seven_days_ago,
                ApiHit.response_time_ms.isnot(None)
            ).group_by(func.extract('dow', ApiHit.created_at)).order_by('day_of_week')
        )
        weekly_performance = result.all()

        # Metryki systemowe (jeśli istnieją)
        result = await db.execute(
            select(
                SystemMetrics.metric_name,
                func.avg(SystemMetrics.metric_value).label('avg_value'),
                func.max(SystemMetrics.metric_value).label('max_value'),
                func.min(SystemMetrics.metric_value).label('min_value')
            ).filter(
                SystemMetrics.created_at >= seven_days_ago
            ).group_by(SystemMetrics.metric_name)
        )
        system_metrics = result.all()

        # P95 i P99 percentyle czasów odpowiedzi
        result = await db.execute(
            select(
                func.percentile_cont(0.95).within_group(ApiHit.response_time_ms).label('p95'),
                func.percentile_cont(0.99).within_group(ApiHit.response_time_ms).label('p99')
            ).filter(
                ApiHit.created_at >= seven_days_ago,
                ApiHit.response_time_ms.isnot(None)
            )
        )
        percentiles = result.first()

        return {
            "hourly_performance": [
                {
                    "hour": int(perf[0]),
                    "avg_response_time_ms": round(perf[1] or 0, 2),
                    "request_count": perf[2]
                }
                for perf in hourly_performance
            ],
            "slowest_endpoints": [
                {
                    "endpoint": endpoint[0],
                    "method": endpoint[1],
                    "avg_response_time_ms": round(endpoint[2] or 0, 2),
                    "request_count": endpoint[3]
                }
                for endpoint in slowest_endpoints
            ],
            "weekly_performance": [
                {
                    "day_of_week": int(perf[0]),
                    "avg_response_time_ms": round(perf[1] or 0, 2),
                    "request_count": perf[2]
                }
                for perf in weekly_performance
            ],
            "system_metrics": [
                {
                    "metric_name": metric[0],
                    "avg_value": round(metric[1] or 0, 2),
                    "max_value": round(metric[2] or 0, 2),
                    "min_value": round(metric[3] or 0, 2)
                }
                for metric in system_metrics
            ],
            "response_time_percentiles": {
                "p95_ms": round(percentiles[0] or 0, 2),
                "p99_ms": round(percentiles[1] or 0, 2)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Błąd podczas pobierania statystyk wydajności: {str(e)}"
        )


@router.get("/tests/stats")
async def get_tests_statistics(
        current_user: User = Depends(auth_service.get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Pobiera statystyki testów psychologicznych.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    try:
        # Testy według typu
        result = await db.execute(
            select(
                PsychologicalTest.test_type,
                func.count(PsychologicalTest.id).label('count'),
                func.avg(PsychologicalTest.score).label('avg_score')
            ).group_by(PsychologicalTest.test_type)
        )
        tests_by_type = result.all()

        # Testy według dnia (ostatnie 30 dni)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        result = await db.execute(
            select(
                func.date(PsychologicalTest.created_at).label('date'),
                func.count(PsychologicalTest.id).label('count')
            ).filter(
                PsychologicalTest.created_at >= thirty_days_ago
            ).group_by(func.date(PsychologicalTest.created_at)).order_by(desc('date'))
        )
        tests_by_day = result.all()

        # Testy według użytkownika
        result = await db.execute(
            select(
                User.username,
                func.count(PsychologicalTest.id).label('test_count'),
                func.avg(PsychologicalTest.score).label('avg_score')
            ).join(PsychologicalTest).group_by(User.id, User.username).order_by(
                desc('test_count')
            ).limit(20)
        )
        tests_by_user = result.all()

        # Rozkład wyników według zakresów
        result = await db.execute(
            select(
                PsychologicalTest.test_type,
                func.case(
                    (PsychologicalTest.score < 5, "Niski"),
                    (PsychologicalTest.score < 10, "Średni"),
                    (PsychologicalTest.score < 15, "Wysoki"),
                    else_="Bardzo wysoki"
                ).label('score_range'),
                func.count(PsychologicalTest.id).label('count')
            ).filter(
                PsychologicalTest.score.isnot(None)
            ).group_by(PsychologicalTest.test_type, 'score_range')
        )
        score_distribution = result.all()

        return {
            "tests_by_type": [
                {
                    "test_type": test[0],
                    "count": test[1],
                    "avg_score": round(test[2] or 0, 2)
                }
                for test in tests_by_type
            ],
            "tests_by_day": [
                {
                    "date": str(test[0]),
                    "count": test[1]
                }
                for test in tests_by_day
            ],
            "tests_by_user": [
                {
                    "username": user[0],
                    "test_count": user[1],
                    "avg_score": round(user[2] or 0, 2)
                }
                for user in tests_by_user
            ],
            "score_distribution": [
                {
                    "test_type": dist[0],
                    "score_range": dist[1],
                    "count": dist[2]
                }
                for dist in score_distribution
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Błąd podczas pobierania statystyk testów: {str(e)}"
        )
