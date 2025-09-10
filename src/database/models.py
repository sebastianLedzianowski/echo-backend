from enum import Enum
from sqlalchemy import Column, Integer, String, func, Text, JSON, Float
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql.sqltypes import DateTime, Boolean
from sqlalchemy.sql.schema import ForeignKey

Base = declarative_base()


class ConversationMode(str, Enum):
    """Tryby konwersacji dostępne w systemie"""
    EMPATHETIC = "empathetic"
    PRACTICAL = "practical"
    DIARY = "diary"


class TestType(str, Enum):
    """Typy testów psychologicznych dostępne w systemie"""
    ASRS = "asrs"
    GAD7 = "gad7"
    PHQ9 = "phq9"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True)
    password = Column(String(255), nullable=False)
    email = Column(String(250), nullable=True, unique=True)
    full_name = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=func.now())
    refresh_token = Column(String(255), nullable=True)
    confirmed = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    diary_entries = relationship(
        "DiaryEntry", back_populates="user", cascade="all, delete"
    )
    conversation_history = relationship(
        "ConversationHistory", back_populates="user", cascade="all, delete"
    )
    psychological_tests = relationship(
        "PsychologicalTest", back_populates="user", cascade="all, delete"
    )
    api_hits = relationship(
        "ApiHit", back_populates="user", cascade="all, delete"
    )
    llm_metrics = relationship(
        "LLMMetrics", back_populates="user", cascade="all, delete"
    )

    def dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "password": self.password,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at,
            "refresh_token": self.refresh_token,
            "confirmed": self.confirmed,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
        }


class DiaryEntry(Base):
    __tablename__ = "diary_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime, default=func.now())
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    emotion_tags = Column(Text, nullable=True)

    user = relationship("User", back_populates="diary_entries")

    def dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "title": self.title,
            "content": self.content,
            "emotion_tags": self.emotion_tags,
        }


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    mode = Column(
        SQLEnum(ConversationMode, name="conversation_mode"), nullable=False
    )
    message = Column(Text, nullable=False)
    is_user_message = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="conversation_history")

    def dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "mode": self.mode.value,
            "message": self.message,
            "is_user_message": self.is_user_message,
            "created_at": self.created_at,
        }


class PsychologicalTest(Base):
    __tablename__ = "psychological_tests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    test_type = Column(String(20), nullable=False)  # asrs, gad7, phq9
    answers = Column(JSON, nullable=False)  # JSON z odpowiedziami użytkownika
    score = Column(Float, nullable=True)  # Wynik punktowy testu
    interpretation = Column(Text, nullable=True)  # Interpretacja AI
    ai_analysis = Column(Text, nullable=True)  # Szczegółowa analiza AI
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="psychological_tests")

    def dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "test_type": self.test_type.value,
            "answers": self.answers,
            "score": self.score,
            "interpretation": self.interpretation,
            "ai_analysis": self.ai_analysis,
            "created_at": self.created_at,
        }


class ApiHit(Base):
    __tablename__ = "api_hits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )  # Nullable dla anonimowych użytkowników
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(Text, nullable=True)
    response_status = Column(Integer, nullable=False)
    response_time_ms = Column(Float, nullable=True)  # Czas w ms
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="api_hits")

    def dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "response_status": self.response_status,
            "response_time_ms": self.response_time_ms,
            "created_at": self.created_at,
        }


class SystemMetrics(Base):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_unit = Column(String(20), nullable=True)  # ms, MB, count, etc.
    metric_metadata = Column(JSON, nullable=True)  # Dodatkowe info
    created_at = Column(DateTime, default=func.now())

    def dict(self):
        return {
            "id": self.id,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "metric_unit": self.metric_unit,
            "metric_metadata": self.metric_metadata,
            "created_at": self.created_at,
        }


class LLMMetrics(Base):
    __tablename__ = "llm_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )  # Nullable dla anonimowych użytkowników
    endpoint = Column(String(255), nullable=False)  # Endpoint który wywołał LLM
    model_name = Column(String(100), nullable=True)  # Nazwa modelu LLM
    prompt_tokens = Column(Integer, nullable=True)  # Liczba tokenów w prompt
    completion_tokens = Column(Integer, nullable=True)  # Liczba tokenów w odpowiedzi
    total_tokens = Column(Integer, nullable=True)  # Całkowita liczba tokenów
    response_time_ms = Column(Float, nullable=False)  # Czas odpowiedzi LLM w ms
    cost_usd = Column(Float, nullable=True)  # Koszt w USD (jeśli dostępny)
    temperature = Column(Float, nullable=True)  # Temperatura modelu
    max_tokens = Column(Integer, nullable=True)  # Maksymalna liczba tokenów
    success = Column(Boolean, default=True)  # Czy odpowiedź była udana
    error_message = Column(Text, nullable=True)  # Komunikat błędu jeśli wystąpił
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="llm_metrics")

    def dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "endpoint": self.endpoint,
            "model_name": self.model_name,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "response_time_ms": self.response_time_ms,
            "cost_usd": self.cost_usd,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "success": self.success,
            "error_message": self.error_message,
            "created_at": self.created_at,
        }
