from sqlalchemy import Column, Integer, String, func, Text
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql.sqltypes import DateTime, Boolean
from sqlalchemy.sql.schema import ForeignKey

Base = declarative_base()

from enum import Enum
from sqlalchemy import Enum as SQLEnum


class ConversationMode(str, Enum):
    """Tryby konwersacji dostępne w systemie"""
    EMPATHETIC = "empathetic"
    PRACTICAL = "practical"
    DIARY = "diary"


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

    diary_entries = relationship("DiaryEntry", back_populates="user", cascade="all, delete")
    conversation_history = relationship("ConversationHistory", back_populates="user", cascade="all, delete")

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
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)

    user = relationship("User", back_populates="diary_entries")

    def dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "title": self.title,
            "content": self.content,
        }


class ConversationHistory(Base):
    __tablename__ = "conversation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mode = Column(SQLEnum(ConversationMode, name="conversation_mode"), nullable=False)
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
