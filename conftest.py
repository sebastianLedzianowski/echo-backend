import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.db import get_db
from src.database.models import Base
from main import app


# Konfiguracja testowej bazy danych SQLite
TEST_SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# Synchroniczny silnik dla testów
test_engine = create_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Sesja dla testów
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)


@pytest.fixture(scope="session")
def test_db_setup():
    """Konfiguruje testową bazę danych."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(test_db_setup):
    """Tworzy sesję bazy danych dla testów."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session) -> Generator:
    """Tworzy klienta testowego FastAPI."""
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Dane testowego użytkownika."""
    return {
        "username": "testuser",
        "password": "testpassword123",
        "email": "test@example.com",
        "full_name": "Test User"
    }


@pytest.fixture
def test_user_login_data():
    """Dane logowania testowego użytkownika."""
    return {
        "username": "testuser",
        "password": "testpassword123"
    }


@pytest.fixture
def admin_user_data():
    """Dane testowego administratora."""
    return {
        "username": "admin",
        "password": "adminpassword123",
        "email": "admin@example.com",
        "full_name": "Admin User"
    }
