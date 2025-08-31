# Konfiguracja

## Zmienne środowiskowe

### Baza danych
```env
# PostgreSQL
POSTGRES_USER=echo_user
POSTGRES_PASSWORD=echo_password
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=echo_db

# Połączenie
SQLALCHEMY_DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_SERVER}:${POSTGRES_PORT}/${POSTGRES_DB}
SQL_ECHO=false
```

### Redis
```env
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_SSL=false

# Cache
CACHE_TTL=1800  # 30 minut
CACHE_PREFIX=echo
```

### Bezpieczeństwo
```env
# JWT
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
CORS_METHODS=*
CORS_HEADERS=*
```

### Email
```env
# SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your-password
SMTP_TLS=true
SMTP_SSL=false

# Sender
MAIL_FROM=noreply@example.com
MAIL_FROM_NAME=Echo Backend
```

### AI
```env
# Ollama
OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OLLAMA_TIMEOUT=30

# Limity
MAX_INPUT_LENGTH=1000
MAX_OUTPUT_LENGTH=2000
RATE_LIMIT_PER_USER=100
```

## Docker

### docker-compose.yml
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=db
      - REDIS_HOST=redis
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:13
    environment:
      - POSTGRES_USER=echo_user
      - POSTGRES_PASSWORD=echo_password
      - POSTGRES_DB=echo_db
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Ustawienia aplikacji

### config.py
```python
from pydantic import BaseSettings, EmailStr, PostgresDsn, RedisDsn

class Settings(BaseSettings):
    # Aplikacja
    APP_NAME: str = "Echo Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Baza danych
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str
    POSTGRES_PORT: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URL: PostgresDsn | None = None
    
    # Redis
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str | None = None
    REDIS_SSL: bool = False
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Email
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    MAIL_FROM: EmailStr
    MAIL_FROM_NAME: str
    
    # AI
    OLLAMA_API_URL: str
    OLLAMA_MODEL: str
    OLLAMA_TIMEOUT: int = 30
    MAX_INPUT_LENGTH: int = 1000
    MAX_OUTPUT_LENGTH: int = 2000
    RATE_LIMIT_PER_USER: int = 100
    
    # Cache
    CACHE_TTL: int = 1800
    CACHE_PREFIX: str = "echo"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

## Logowanie

### logging.conf
```ini
[loggers]
keys=root,echo_backend

[handlers]
keys=console,file

[formatters]
keys=json

[logger_root]
level=INFO
handlers=console

[logger_echo_backend]
level=INFO
handlers=console,file
qualname=echo_backend
propagate=0

[handler_console]
class=StreamHandler
formatter=json
args=(sys.stdout,)

[handler_file]
class=handlers.TimedRotatingFileHandler
formatter=json
args=('logs/app.log', 'midnight', 1, 30)

[formatter_json]
class=pythonjsonlogger.jsonlogger.JsonFormatter
format=%(asctime)s %(name)s %(levelname)s %(message)s
```

## Makefile

### Makefile
```makefile
.PHONY: install run test lint clean

install:
	python -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt

run:
	uvicorn main:app --reload

test:
	pytest --cov=src

lint:
	black src tests
	ruff src tests

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".coverage" -exec rm {} +
```

## Skrypty

### init-db.py
```python
from src.database.models import Base
from src.database.db import engine

def init_db():
    """Inicjalizuje bazę danych."""
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
```

### init-scripts/01-init-db.sql
```sql
-- Użytkownicy
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(250) UNIQUE,
    full_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    refresh_token VARCHAR(255),
    confirmed BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE
);

-- Dziennik
CREATE TABLE diary_entries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    title VARCHAR(200),
    content TEXT NOT NULL,
    emotion_tags VARCHAR(500)
);

-- Konwersacje
CREATE TABLE conversation_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    mode VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    is_user_message BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

