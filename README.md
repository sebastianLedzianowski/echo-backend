# Echo Backend

Backend dla platformy wsparcia emocjonalnego i filozoficznego opartej na AI.

## Funkcjonalności

- **Autoryzacja i uwierzytelnianie** użytkowników
- **Generowanie odpowiedzi AI** w różnych trybach (empatyczny, filozoficzny, praktyczny)
- **Dzienniczek emocjonalny** z analizą AI
- **Historia konwersacji** z AI
- **Panel administracyjny** z statystykami systemu
- **API REST** z dokumentacją Swagger

## Wymagania systemowe

- Python 3.11+
- PostgreSQL 17+
- Docker i Docker Compose

## Instalacja i uruchomienie

1. Sklonuj repozytorium:
```bash
git clone <repository-url>
cd echo_backend
```

2. Utwórz środowisko wirtualne:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# lub
.venv\Scripts\activate  # Windows
```

3. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

4. Skonfiguruj zmienne środowiskowe:
```bash
cp env.txt .env
# Edytuj .env według potrzeb
```

5. Uruchom bazę danych:
```bash
docker-compose up -d postgres
```

6. Uruchom aplikację:
```bash
python main.py
```

Aplikacja będzie dostępna pod adresem: http://localhost:8000

## Struktura projektu

```
src/
├── conf/           # Konfiguracja aplikacji
├── core/           # Rdzeń aplikacji (logowanie, wyjątki, walidacja)
├── database/       # Modele bazy danych i migracje
├── repository/     # Warstwa dostępu do danych
├── routes/         # Endpointy API
├── services/       # Logika biznesowa (AI, email, autoryzacja)
└── schemas.py      # Schematy Pydantic
```

## API Endpoints

### Autoryzacja
- `POST /api/auth/signup` - Rejestracja użytkownika
- `POST /api/auth/login` - Logowanie
- `GET /api/auth/refresh_token` - Odświeżenie tokenu

### Użytkownicy
- `GET /api/users/me/` - Profil zalogowanego użytkownika
- `PATCH /api/users/me/` - Aktualizacja profilu
- `PATCH /api/users/me/password/` - Zmiana hasła

### AI i Konwersacje
- `POST /api/echo/empathetic/send` - Empatyczne odpowiedzi AI
- `POST /api/echo/philosophical/send` - Filozoficzne odpowiedzi AI
- `POST /api/echo/practical/send` - Praktyczne odpowiedzi AI
- `POST /api/echo/diary/send` - Wpis do dziennika emocji (bez AI)
- `GET /api/echo/empathetic/history` - Historia konwersacji empatycznych
- `GET /api/echo/philosophical/history` - Historia konwersacji filozoficznych
- `GET /api/echo/practical/history` - Historia konwersacji praktycznych
- `GET /api/echo/diary/history` - Historia wpisów do dziennika
- `GET /api/echo/diary/entries` - Lista wpisów dziennika
- `POST /api/echo/diary/entries` - Tworzenie wpisu dziennika

### Panel Administracyjny
- `GET /api/admin/dashboard/overview` - Przegląd systemu
- `GET /api/admin/users` - Lista użytkowników
- `GET /api/admin/dashboard/system/health` - Status zdrowia systemu

## Tryby AI

- **empathetic** - Empatyczne wsparcie emocjonalne
- **philosophical** - Filozoficzne rozważania
- **practical** - Praktyczne rady
- **diary** - Dziennik emocji (bez AI)

## Bezpieczeństwo

- JWT tokeny z refresh
- Hashowanie haseł (bcrypt)
- Walidacja danych wejściowych
- CORS middleware
- Trusted Host middleware

## Rozwój

### Uruchomienie testów
```bash
pytest
```

### Formatowanie kodu
```bash
black src/
isort src/
```

### Linting
```bash
flake8 src/
```

## Licencja

MIT License