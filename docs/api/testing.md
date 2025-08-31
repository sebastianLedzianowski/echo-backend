# Testowanie API

## Struktura testów

```
tests/
├── conftest.py              # Fixtures i konfiguracja
├── pytest.ini              # Konfiguracja pytest
├── test_main.py            # Testy głównej aplikacji
├── test_conversation_history.py  # Testy historii konwersacji
├── test_repository/        # Testy warstwy dostępu do danych
│   ├── __init__.py
│   └── test_repository_users.py
├── tests_routes/          # Testy endpointów
│   ├── __init__.py
│   ├── test_admin_dashboard.py
│   ├── test_routes_admin.py
│   ├── test_routes_auth.py
│   ├── test_routes_echo.py
│   └── test_routes_users.py
└── tests_services/        # Testy logiki biznesowej
    ├── __init__.py
    ├── test_ai.py
    ├── test_encryption.py
    ├── test_mailer.py
    └── test_services_auth.py
```

## Uruchamianie testów

### Wszystkie testy
```bash
pytest
```

### Konkretny moduł
```bash
pytest tests/test_routes/test_routes_auth.py
```

### Z pokryciem kodu
```bash
pytest --cov=src
```

### Z raportem HTML
```bash
pytest --cov=src --cov-report=html
```

## Fixtures

### Baza danych
```python
@pytest.fixture
def db():
    """Tworzy testową bazę danych."""
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
```

### Redis
```python
@pytest.fixture
def redis():
    """Tworzy testową instancję Redis."""
    redis = FakeRedis()
    yield redis
    redis.flushall()
```

### Użytkownicy
```python
@pytest.fixture
def user():
    """Tworzy testowego użytkownika."""
    return User(
        username="testuser",
        email="test@example.com",
        password="hashedpass",
        is_active=True,
        confirmed=True
    )

@pytest.fixture
def admin_user():
    """Tworzy testowego administratora."""
    return User(
        username="admin",
        email="admin@example.com",
        password="hashedpass",
        is_active=True,
        confirmed=True,
        is_admin=True
    )
```

### Tokeny
```python
@pytest.fixture
def access_token(user):
    """Generuje testowy access token."""
    return auth_service.create_token(
        subject=user.username,
        scope="access_token"
    )

@pytest.fixture
def refresh_token(user):
    """Generuje testowy refresh token."""
    return auth_service.create_token(
        subject=user.username,
        scope="refresh_token"
    )
```

## Przykłady testów

### Test endpointu
```python
async def test_login_success(client, user, db):
    # Given
    db.add(user)
    db.commit()
    
    # When
    response = await client.post("/api/auth/login", json={
        "username": user.username,
        "password": "password123"
    })
    
    # Then
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
```

### Test repository
```python
async def test_get_user_by_username(db):
    # Given
    user = User(username="test", password="hash")
    db.add(user)
    db.commit()
    
    # When
    result = await repository_users.get_user_by_username(
        "test",
        db
    )
    
    # Then
    assert result is not None
    assert result.username == "test"
```

### Test serwisu
```python
async def test_generate_ai_response():
    # Given
    text = "Test message"
    mode = "echo"
    
    # When
    response = await ai_service.generate_ai_response(
        text,
        mode
    )
    
    # Then
    assert response is not None
    assert len(response) > 0
```

## Mockowanie

### HTTP Client
```python
@pytest.fixture
def mock_http_client(mocker):
    """Mockuje klienta HTTP."""
    return mocker.patch("httpx.AsyncClient.post")
```

### Redis
```python
@pytest.fixture
def mock_redis(mocker):
    """Mockuje Redis."""
    mock = mocker.patch("src.services.redis_service.redis_client")
    mock.get.return_value = None
    return mock
```

### Email
```python
@pytest.fixture
def mock_email_sender(mocker):
    """Mockuje wysyłanie emaili."""
    return mocker.patch("src.services.email.send_email")
```

## Asercje

### Response
```python
def assert_response_ok(response):
    """Sprawdza czy odpowiedź jest poprawna."""
    assert response.status_code == 200
    assert response.json() is not None

def assert_error_response(response, status_code, detail):
    """Sprawdza odpowiedź błędu."""
    assert response.status_code == status_code
    data = response.json()
    assert "detail" in data
    assert data["detail"] == detail
```

### Model
```python
def assert_user_fields(user, expected):
    """Sprawdza pola użytkownika."""
    assert user.username == expected["username"]
    assert user.email == expected.get("email")
    assert user.is_active == expected.get("is_active", True)
```

### Cache
```python
def assert_cache_hit(redis_mock, key):
    """Sprawdza trafienie w cache."""
    redis_mock.get.assert_called_once_with(key)

def assert_cache_miss(redis_mock, key):
    """Sprawdza pudło w cache."""
    redis_mock.get.assert_called_once_with(key)
    assert redis_mock.set.called
```

## Pokrycie kodu

### Minimalne wymagania
- Całość: 80%
- Routes: 90%
- Services: 85%
- Repository: 90%
- Models: 75%

### Raportowanie
```bash
# Generowanie raportu
pytest --cov=src --cov-report=term-missing

# Eksport do XML
pytest --cov=src --cov-report=xml

# Eksport do HTML
pytest --cov=src --cov-report=html
```

## CI/CD

### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest --cov=src
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

### Pre-commit
```yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
```

