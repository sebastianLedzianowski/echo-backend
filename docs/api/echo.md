# Konwersacje AI

## Endpointy

### 1. Empatyczne odpowiedzi (Echo)
```http
POST /api/echo/empathetic/send
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "text": "string"
}
```

**Response:**
```json
{
    "ai_response": "string",
    "updated_history": [...]
}
```

### 2. Filozoficzne odpowiedzi (Question)
```http
POST /api/echo/philosophical/send
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "text": "string"
}
```

**Response:**
```json
{
    "ai_response": "string",
    "updated_history": [...]
}
```

### 3. Praktyczne odpowiedzi (Practical)
```http
POST /api/echo/practical/send
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "text": "string"
}
```

**Response:**
```json
{
    "ai_response": "string",
    "updated_history": [...]
}
```

### 4. Dziennik emocji (bez AI)
```http
POST /api/echo/diary/send
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "text": "string"
}
```

**Response:**
```json
{
    "message": "Wpis został zapisany w dzienniczku",
    "entry": {
        "id": "integer",
        "content": "string",
        "created_at": "datetime"
    },
    "updated_history": [...]
}
```

## Historia konwersacji

### Historia dla każdego trybu
```http
GET /api/echo/empathetic/history
GET /api/echo/philosophical/history
GET /api/echo/practical/history
GET /api/echo/diary/history
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "conversations": [
        {
            "user_message": "string",
            "ai_response": "string",
            "created_at": "datetime"
        }
    ]
}
```

### Zarządzanie dziennikiem
```http
GET /api/echo/diary/entries
POST /api/echo/diary/entries
```

**Query Parameters dla GET:**
- `skip`: integer (domyślnie 0)
- `limit`: integer (domyślnie 50)

## Tryby Konwersacji

### Empatyczne odpowiedzi (Echo)
- Empatyczne odpowiedzi
- Aktywne słuchanie
- Odzwierciedlanie emocji
- Brak oceniania
- Zachęcanie do ekspresji

### Filozoficzne odpowiedzi (Question)
- Odpowiedzi na pytania filozoficzne
- Głębsza analiza
- Różne perspektywy
- Zachęcanie do refleksji
- Odwołania do filozofii

### Praktyczne odpowiedzi (Practical)
- Konkretne porady
- Rozwiązania problemów
- Akcje do wykonania
- Planowanie
- Implementacja

### Dziennik emocji (Diary)
- Zapis emocji bez AI
- Prywatne notatki
- Śledzenie nastrojów
- Refleksje osobiste
- Brak generowania odpowiedzi

## Walidacja

### Wiadomość użytkownika
- 1-2000 znaków
- Bez HTML i znaków kontrolnych
- Bez nadmiarowych białych znaków

## Cache

### Odpowiedzi AI
- Cachowane przez 1 godzinę
- Klucz: `ai:response:{hash}`
- Hash generowany z tekstu i trybu
- Osobny cache dla każdego trybu

### Historia
- Cachowana przez 5 minut
- Klucze:
  - `conversation:user:{user_id}:mode:{mode}:latest`
  - `conversation:user:{user_id}:mode:{mode}:full`

## Przykłady

### Empatyczna odpowiedź
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.post(
    "/api/echo/empathetic/send",
    headers=headers,
    json={"text": "Czuję się dziś smutny..."}
)
```

### Filozoficzna odpowiedź
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.post(
    "/api/echo/philosophical/send",
    headers=headers,
    json={"text": "Czym jest szczęście?"}
)
```

### Praktyczna odpowiedź
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.post(
    "/api/echo/practical/send",
    headers=headers,
    json={"text": "Jak zorganizować swój czas?"}
)
```

### Wpis do dziennika
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.post(
    "/api/echo/diary/send",
    headers=headers,
    json={"text": "Dzisiaj czuję się spokojny..."}
)
```

### Pobranie historii
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.get(
    "/api/echo/empathetic/history",
    headers=headers
)
```

## Limity i Ograniczenia

### Rate Limiting
- 60 requestów na minutę na użytkownika
- 1000 requestów na godzinę na użytkownika
- Osobne limity dla każdego trybu

### Długość odpowiedzi
- Empatyczne: max 500 znaków
- Filozoficzne: max 1000 znaków
- Praktyczne: max 800 znaków
- Dziennik: bez limitu (tylko zapis)

### Historia
- Przechowywana przez 30 dni
- Maksymalnie 1000 wiadomości na tryb
- Automatyczne czyszczenie starszych

