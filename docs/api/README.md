# Echo Backend API Documentation

## Overview

Echo Backend to API dla platformy wsparcia emocjonalnego i filozoficznego. API zostało zbudowane przy użyciu FastAPI i oferuje następujące główne funkcjonalności:

- Uwierzytelnianie i autoryzacja użytkowników
- Zarządzanie profilami użytkowników
- Dziennik emocji ("Szuflada emocji")
- Konwersacje AI w różnych trybach
- Panel administracyjny

## Technologie

- FastAPI
- PostgreSQL
- Redis (cache)
- SQLAlchemy (ORM)
- Pydantic (walidacja)
- JWT (tokeny)

## Wymagania

- Python 3.9+
- PostgreSQL 13+
- Redis 6+

## Instalacja

1. Sklonuj repozytorium
2. Utwórz wirtualne środowisko: `python -m venv .venv`
3. Aktywuj środowisko: `source .venv/bin/activate`
4. Zainstaluj zależności: `pip install -r requirements.txt`
5. Skopiuj `env.txt` do `.env` i uzupełnij zmienne
6. Uruchom migracje: `python init-db.py`
7. Uruchom serwer: `uvicorn main:app --reload`

## Struktura API

### Autentykacja

Wszystkie chronione endpointy wymagają tokenu JWT w nagłówku:
```
Authorization: Bearer <token>
```

Token można uzyskać poprzez:
- POST `/api/auth/login`
- POST `/api/auth/refresh_token`

### Endpointy

#### Autentykacja
- POST `/api/auth/signup` - Rejestracja
- POST `/api/auth/login` - Logowanie
- POST `/api/auth/refresh_token` - Odświeżenie tokenu
- GET `/api/auth/confirmed_email/{token}` - Potwierdzenie email
- POST `/api/auth/request_email` - Prośba o ponowne wysłanie maila
- POST `/api/auth/request_password_reset` - Reset hasła
- POST `/api/auth/reset_password` - Ustawienie nowego hasła

#### Użytkownicy
- GET `/api/users/me` - Profil użytkownika
- PATCH `/api/users/me` - Aktualizacja profilu
- PATCH `/api/users/me/password` - Zmiana hasła
- DELETE `/api/users/me` - Usunięcie konta

#### Dziennik
- POST `/api/diary/entries` - Nowy wpis
- GET `/api/diary/entries` - Lista wpisów
- GET `/api/diary/entries/{entry_id}` - Szczegóły wpisu
- PUT `/api/diary/entries/{entry_id}` - Edycja wpisu
- DELETE `/api/diary/entries/{entry_id}` - Usunięcie wpisu
- GET `/api/diary/emotion-tags` - Lista tagów emocji

#### Konwersacje
- POST `/api/echo/generate-response` - Nowa odpowiedź
- GET `/api/echo/conversation-history/{user_id}` - Historia konwersacji
- GET `/api/echo/full-conversation-history/{user_id}` - Pełna historia

#### Panel Admina
- GET `/api/admin/dashboard/overview` - Przegląd systemu
- GET `/api/admin/dashboard/users/stats` - Statystyki użytkowników
- GET `/api/admin/dashboard/diary/stats` - Statystyki dziennika
- GET `/api/admin/dashboard/conversations/stats` - Statystyki konwersacji
- GET `/api/admin/dashboard/redis/info` - Informacje Redis
- GET `/api/admin/dashboard/system/health` - Stan systemu

## Modele Danych

### User
```python
{
    "id": int,
    "username": str,
    "email": str | None,
    "full_name": str | None,
    "created_at": datetime,
    "confirmed": bool,
    "is_active": bool,
    "is_admin": bool
}
```

### DiaryEntry
```python
{
    "id": int,
    "user_id": int,
    "created_at": datetime,
    "title": str | None,
    "content": str,
    "emotion_tags": str | None
}
```

### ConversationHistory
```python
{
    "id": int,
    "user_id": int,
    "mode": str,
    "message": str,
    "is_user_message": bool,
    "created_at": datetime
}
```

## Walidacja

API używa Pydantic do walidacji requestów i odpowiedzi. Główne zasady:

### Hasła
- Minimum 6 znaków
- Przynajmniej 1 wielka litera
- Przynajmniej 1 mała litera
- Przynajmniej 1 cyfra
- Przynajmniej 1 znak specjalny

### Nazwy użytkowników
- 5-55 znaków
- Tylko litery, cyfry i podkreślenia
- Musi zaczynać się od litery
- Bez kolejnych podkreśleń

### Email
- Poprawny format
- Unikalne w systemie
- Wymagane potwierdzenie

### Tagi emocji
- Rozdzielone przecinkami
- Maksymalnie 10 tagów
- 1-20 znaków na tag
- Bez duplikatów

## Obsługa Błędów

API zwraca ustandaryzowane odpowiedzi błędów:

```json
{
    "detail": "Opis błędu",
    "type": "TypBłędu"
}
```

Główne kody błędów:
- 400: Nieprawidłowe żądanie
- 401: Brak autoryzacji
- 403: Brak uprawnień
- 404: Nie znaleziono
- 409: Konflikt
- 422: Błąd walidacji
- 500: Błąd serwera

## Paginacja

Endpointy zwracające listy wspierają paginację:

```json
{
    "data": [...],
    "metadata": {
        "total": int,
        "page": int,
        "pages": int,
        "has_next": bool,
        "has_prev": bool
    }
}
```

Parametry:
- `skip`: Liczba pominiętych rekordów
- `limit`: Liczba rekordów na stronę (max 1000)

## Cache

API używa Redis do cachowania:
- Dane użytkowników (30 minut)
- Odpowiedzi AI (1 godzina)
- Statystyki (5 minut)

## Logowanie

System loguje:
- Wszystkie requesty HTTP
- Błędy aplikacji
- Operacje na bazie danych
- Działania administratorów

Logi są zapisywane do:
- Plików (logs/app_YYYYMMDD.log)
- Konsoli (w trybie dev)

## Bezpieczeństwo

- Wszystkie hasła są hashowane (bcrypt)
- Tokeny JWT z krótkim czasem życia
- CORS z ograniczonymi origin
- Rate limiting
- Walidacja danych wejściowych
- Sanityzacja danych wyjściowych

## Monitoring

System zbiera metryki:
- Liczba requestów
- Czasy odpowiedzi
- Użycie zasobów
- Błędy i wyjątki
- Statystyki cache
- Obciążenie bazy danych

