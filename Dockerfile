# 1. Wybór obrazu Pythona
FROM python:3.11-slim

# 2. Zmienne środowiskowe
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# 3. Instalacja zależności systemowych
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libffi-dev \
    python3-dev \
    git \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 4. Utwórz katalog aplikacji
WORKDIR /app

# 5. Skopiuj tylko pliki do instalacji zależności
COPY pyproject.toml poetry.lock /app/

# 6. Instalacja Poetry i zależności
RUN pip install --upgrade pip \
    && pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

# 7. Skopiuj całą aplikację (kod, main.py, alembic itd.)
COPY . /app

# 8. Wystaw port
EXPOSE 8000

# 9. Kopia entrypoint i nadanie uprawnień
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 10. Start kontenera
ENTRYPOINT ["/entrypoint.sh"]
