import pytest
import pytest_asyncio
import uuid
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import text
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock

from src.database.models import Base, User
from src.database.db import get_db
from src.routes.auth import router as auth_router
from src.routes.users import router as users_router
from src.routes.admin import router as admin_router
from src.routes.admin_dashboard import router as admin_dashboard_router
from src.routes.echo import router as echo_router
from src.services.auth import auth_service

# Test DB w pamięci (RAM)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Tworzymy silnik asynchroniczny
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool  # potrzebne, żeby zachować 1 bazę w wielu połączeniach
)

# Session factory – bez bindowania, bindujemy w fixture
TestSessionMaker = async_sessionmaker(
    expire_on_commit=False,
    class_=AsyncSession,
)


# --- FIXTURES --- #

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Tworzymy schemat bazy w pamięci raz na całą sesję testową"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """
    Każdy test dostaje nową transakcję,
    rollback po teście przywraca czystą bazę.
    """
    async with test_engine.connect() as connection:
        trans = await connection.begin()
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest_asyncio.fixture
async def app(db_session):
    """Aplikacja FastAPI z podmienionym dependency DB"""
    test_app = FastAPI()
    test_app.include_router(auth_router, prefix="/api")
    test_app.include_router(users_router, prefix="/api")
    test_app.include_router(admin_router, prefix="/api")
    test_app.include_router(admin_dashboard_router, prefix="/api")
    test_app.include_router(echo_router, prefix="/api")

    async def _get_test_db():
        yield db_session

    test_app.dependency_overrides[get_db] = _get_test_db
    return test_app


@pytest_asyncio.fixture
async def client(app):
    """Asynchroniczny klient testowy dla FastAPI"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
def mock_email_service(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr("src.services.email.email_service.send_email", mock)
    return mock


@pytest_asyncio.fixture
def user_data():
    class UserTest:
        def __init__(self):
            self.username = "deadpool"
            self.email = "deadpool@example.com"
            self.password = "ValidPass123!"
            self.full_name = "Dead Pool"

        def dict(self):
            return {
                "username": self.username,
                "email": self.email,
                "password": self.password,
                "full_name": self.full_name,
            }
    return UserTest()

async def create_user_db(body, db: AsyncSession):
    new_user = User(**body.dict())
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def login_user_confirmed_true_and_hash_password(user, db: AsyncSession):
    hashed_password = auth_service.get_password_hash(user.password)
    new_user = await create_user_db(user, db)
    new_user.password = hashed_password
    new_user.confirmed = True
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def login_user_token_created(user, db: AsyncSession):
    new_user = await login_user_confirmed_true_and_hash_password(user, db)
    access_token = auth_service.create_token(subject=new_user.email, scope="access_token")
    refresh_token = auth_service.create_token(subject=new_user.email, scope="refresh_token")
    new_user.refresh_token = refresh_token
    await db.commit()
    await db.refresh(new_user)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

async def create_admin_user(user_data, db_session: AsyncSession):
    admin_user_data = user_data.dict()
    admin_user_data["username"] = f"admin_{uuid.uuid4().hex[:8]}"
    admin_user_data["email"] = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    admin = User(**admin_user_data)
    admin.password = auth_service.get_password_hash(admin.password)
    admin.is_admin = True
    admin.confirmed = True
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin

async def create_regular_user(user_data, db_session: AsyncSession, suffix: str = ""):
    user_data_dict = user_data.dict()
    user_data_dict["username"] = f"user_{uuid.uuid4().hex[:8]}{suffix}"
    user_data_dict["email"] = f"user_{uuid.uuid4().hex[:8]}{suffix}@example.com"
    user = User(**user_data_dict)
    user.password = auth_service.get_password_hash(user.password)
    user.confirmed = True
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

async def create_diary_entry(user_id: int, db: AsyncSession, days_ago: int = 0, emotion_tags: str = "happy,calm"):
    """Tworzy wpis w dzienniku"""
    from src.database.models import DiaryEntry
    from datetime import datetime, timedelta
    
    entry = DiaryEntry(
        user_id=user_id,
        title="Test Entry",
        content="Test Content",
        emotion_tags=emotion_tags
    )
    if days_ago > 0:
        entry.created_at = datetime.utcnow() - timedelta(days=days_ago)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry

async def create_conversation(
    user_id: int,
    db: AsyncSession,
    days_ago: int = 0,
    mode: str = "empathetic",
    is_user_message: bool = True
):
    """Tworzy wiadomość w konwersacji"""
    from src.database.models import ConversationHistory
    from datetime import datetime, timedelta
    
    message = ConversationHistory(
        user_id=user_id,
        message="Test message",
        mode=mode,
        is_user_message=is_user_message
    )
    if days_ago > 0:
        message.created_at = datetime.utcnow() - timedelta(days=days_ago)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message
