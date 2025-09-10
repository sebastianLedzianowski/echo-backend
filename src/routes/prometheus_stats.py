"""
Optimized statistics endpoints using Prometheus metrics
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from datetime import datetime, timedelta
from typing import Dict, Any

from src.database.db import get_db
from src.database.models import User, DiaryEntry, ConversationHistory, LLMMetrics, ApiHit, PsychologicalTest
from src.services.auth import auth_service
from src.services.metrics import registry

router = APIRouter(prefix="/admin/prometheus", tags=["admin-prometheus"])


@router.get("/metrics/summary")
async def get_metrics_summary(
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Pobiera podsumowanie metryk z bazy danych i Prometheus.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    
    try:
        # Pobierz podstawowe statystyki z bazy danych
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)
        
        # Statystyki użytkowników
        total_users_result = await db.execute(select(func.count(User.id)))
        total_users = total_users_result.scalar()
        
        active_users_result = await db.execute(
            select(func.count(User.id)).filter(User.is_active)
        )
        active_users = active_users_result.scalar()
        
        # Statystyki konwersacji
        total_conversations_result = await db.execute(
            select(func.count(ConversationHistory.id))
        )
        total_conversations = total_conversations_result.scalar()
        
        conversations_24h_result = await db.execute(
            select(func.count(ConversationHistory.id))
            .filter(ConversationHistory.created_at >= last_24h)
        )
        conversations_24h = conversations_24h_result.scalar()
        
        # Statystyki dziennika
        total_diary_result = await db.execute(select(func.count(DiaryEntry.id)))
        total_diary = total_diary_result.scalar()
        
        diary_24h_result = await db.execute(
            select(func.count(DiaryEntry.id))
            .filter(DiaryEntry.created_at >= last_24h)
        )
        diary_24h = diary_24h_result.scalar()
        
        # Statystyki LLM
        total_llm_result = await db.execute(select(func.count(LLMMetrics.id)))
        total_llm = total_llm_result.scalar()
        
        llm_24h_result = await db.execute(
            select(func.count(LLMMetrics.id))
            .filter(LLMMetrics.created_at >= last_24h)
        )
        llm_24h = llm_24h_result.scalar()
        
        # Średni czas odpowiedzi LLM
        avg_llm_time_result = await db.execute(
            select(func.avg(LLMMetrics.response_time_ms))
            .filter(
                LLMMetrics.created_at >= last_24h,
                LLMMetrics.success.is_(True),
                LLMMetrics.response_time_ms.isnot(None)
            )
        )
        avg_llm_time = avg_llm_time_result.scalar() or 0
        
        # Statystyki testów psychologicznych
        total_tests_result = await db.execute(select(func.count(PsychologicalTest.id)))
        total_tests = total_tests_result.scalar()
        
        tests_24h_result = await db.execute(
            select(func.count(PsychologicalTest.id))
            .filter(PsychologicalTest.created_at >= last_24h)
        )
        tests_24h = tests_24h_result.scalar()
        
        # Statystyki API
        total_api_result = await db.execute(select(func.count(ApiHit.id)))
        total_api = total_api_result.scalar()
        
        api_24h_result = await db.execute(
            select(func.count(ApiHit.id))
            .filter(ApiHit.created_at >= last_24h)
        )
        api_24h = api_24h_result.scalar()
        
        # Średni czas odpowiedzi API
        avg_api_time_result = await db.execute(
            select(func.avg(ApiHit.response_time_ms))
            .filter(
                ApiHit.created_at >= last_24h,
                ApiHit.response_time_ms.isnot(None)
            )
        )
        avg_api_time = avg_api_time_result.scalar() or 0
        
        # Błędy w ostatnich 24h
        errors_24h_result = await db.execute(
            select(func.count(LLMMetrics.id))
            .filter(
                LLMMetrics.created_at >= last_24h,
                LLMMetrics.success.is_(False)
            )
        )
        errors_24h = errors_24h_result.scalar()
        
        # Wskaźnik błędów
        error_rate = (errors_24h / llm_24h * 100) if llm_24h > 0 else 0
        
        return {
            "timestamp": now.isoformat(),
            "summary": {
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "active_percentage": round((active_users / total_users * 100) if total_users > 0 else 0, 2)
                },
                "conversations": {
                    "total": total_conversations,
                    "last_24h": conversations_24h,
                    "avg_per_hour": round(conversations_24h / 24, 2)
                },
                "diary": {
                    "total_entries": total_diary,
                    "last_24h": diary_24h,
                    "avg_per_hour": round(diary_24h / 24, 2)
                },
                "llm": {
                    "total_calls": total_llm,
                    "last_24h": llm_24h,
                    "avg_response_time_ms": round(avg_llm_time, 2),
                    "avg_per_hour": round(llm_24h / 24, 2)
                },
                "tests": {
                    "total": total_tests,
                    "last_24h": tests_24h,
                    "avg_per_hour": round(tests_24h / 24, 2)
                },
                "api": {
                    "total_requests": total_api,
                    "last_24h": api_24h,
                    "avg_response_time_ms": round(avg_api_time, 2),
                    "avg_per_hour": round(api_24h / 24, 2)
                },
                "errors": {
                    "last_24h": errors_24h,
                    "error_rate_percent": round(error_rate, 2)
                }
            },
            "performance_indicators": {
                "system_health": "healthy" if error_rate < 5 else "warning" if error_rate < 15 else "critical",
                "response_time_status": "good" if avg_llm_time < 2000 else "acceptable" if avg_llm_time < 5000 else "slow",
                "activity_level": "high" if conversations_24h > 100 else "medium" if conversations_24h > 50 else "low"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Błąd podczas pobierania podsumowania metryk: {str(e)}"
        )


@router.get("/metrics/real-time")
async def get_real_time_metrics(
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Pobiera metryki w czasie rzeczywistym z Prometheus.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    
    try:
        # Pobierz metryki z rejestru Prometheus
        metrics_data = {}
        
        # Zbierz wszystkie metryki z rejestru
        for metric in registry.collect():
            metric_name = metric.name
            metric_type = metric.type
            
            if metric_type == 'counter':
                metrics_data[metric_name] = {
                    "type": "counter",
                    "samples": [
                        {
                            "labels": dict(sample.labels),
                            "value": sample.value
                        }
                        for sample in metric.samples
                    ]
                }
            elif metric_type == 'histogram':
                metrics_data[metric_name] = {
                    "type": "histogram",
                    "samples": [
                        {
                            "labels": dict(sample.labels),
                            "value": sample.value
                        }
                        for sample in metric.samples
                    ]
                }
            elif metric_type == 'gauge':
                metrics_data[metric_name] = {
                    "type": "gauge",
                    "samples": [
                        {
                            "labels": dict(sample.labels),
                            "value": sample.value
                        }
                        for sample in metric.samples
                    ]
                }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics_data,
            "total_metrics": len(metrics_data)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Błąd podczas pobierania metryk w czasie rzeczywistym: {str(e)}"
        )


@router.get("/metrics/health")
async def get_metrics_health(
    current_user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Sprawdza zdrowie systemu na podstawie metryk.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Brak uprawnień administratora"
        )
    
    try:
        now = datetime.utcnow()
        last_5m = now - timedelta(minutes=5)
        last_1h = now - timedelta(hours=1)
        
        # Sprawdź aktywność w ostatnich 5 minutach
        recent_activity_result = await db.execute(
            select(func.count(ConversationHistory.id))
            .filter(ConversationHistory.created_at >= last_5m)
        )
        recent_activity = recent_activity_result.scalar()
        
        # Sprawdź błędy w ostatniej godzinie
        recent_errors_result = await db.execute(
            select(func.count(LLMMetrics.id))
            .filter(
                LLMMetrics.created_at >= last_1h,
                LLMMetrics.success.is_(False)
            )
        )
        recent_errors = recent_errors_result.scalar()
        
        # Sprawdź średni czas odpowiedzi w ostatniej godzinie
        avg_response_time_result = await db.execute(
            select(func.avg(LLMMetrics.response_time_ms))
            .filter(
                LLMMetrics.created_at >= last_1h,
                LLMMetrics.success.is_(True),
                LLMMetrics.response_time_ms.isnot(None)
            )
        )
        avg_response_time = avg_response_time_result.scalar() or 0
        
        # Określ status zdrowia
        health_status = "healthy"
        warnings = []
        
        if recent_errors > 10:
            health_status = "warning"
            warnings.append(f"Wysoka liczba błędów w ostatniej godzinie: {recent_errors}")
        
        if avg_response_time > 10000:  # 10 sekund
            health_status = "warning"
            warnings.append(f"Wolny średni czas odpowiedzi: {avg_response_time:.2f}ms")
        
        if recent_activity == 0:
            warnings.append("Brak aktywności w ostatnich 5 minutach")
        
        return {
            "timestamp": now.isoformat(),
            "status": health_status,
            "indicators": {
                "recent_activity_5m": recent_activity,
                "recent_errors_1h": recent_errors,
                "avg_response_time_1h_ms": round(avg_response_time, 2)
            },
            "warnings": warnings,
            "recommendations": [
                "Monitoruj wskaźniki wydajności",
                "Sprawdź logi w przypadku ostrzeżeń",
                "Rozważ skalowanie w przypadku wysokiego obciążenia"
            ] if health_status == "warning" else []
        }
        
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "unhealthy",
            "error": str(e),
            "indicators": {},
            "warnings": ["Błąd podczas sprawdzania zdrowia systemu"],
            "recommendations": ["Sprawdź połączenie z bazą danych"]
        }
