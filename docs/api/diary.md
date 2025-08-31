# Dziennik Emocji

## Endpointy

### Nowy wpis
```http
POST /api/diary/entries
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "title": "string (opcjonalny)",
    "content": "string (1-5000 znaków)",
    "emotion_tags": "string (opcjonalny)"
}
```

**Response:**
```json
{
    "id": "integer",
    "user_id": "integer",
    "created_at": "datetime",
    "title": "string | null",
    "content": "string",
    "emotion_tags": "string | null"
}
```

### Lista wpisów
```http
GET /api/diary/entries
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `skip`: integer (domyślnie 0)
- `limit`: integer (domyślnie 100, max 1000)
- `start_date`: string (format: YYYY-MM-DD)
- `end_date`: string (format: YYYY-MM-DD)
- `emotion_tag`: string

**Response:**
```json
{
    "data": [
        {
            "id": "integer",
            "user_id": "integer",
            "created_at": "datetime",
            "title": "string | null",
            "content": "string",
            "emotion_tags": "string | null"
        }
    ],
    "metadata": {
        "total": "integer",
        "page": "integer",
        "pages": "integer",
        "has_next": "boolean",
        "has_prev": "boolean"
    }
}
```

### Szczegóły wpisu
```http
GET /api/diary/entries/{entry_id}
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "id": "integer",
    "user_id": "integer",
    "created_at": "datetime",
    "title": "string | null",
    "content": "string",
    "emotion_tags": "string | null"
}
```

### Edycja wpisu
```http
PUT /api/diary/entries/{entry_id}
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "title": "string (opcjonalny)",
    "content": "string",
    "emotion_tags": "string (opcjonalny)"
}
```

**Response:**
```json
{
    "id": "integer",
    "user_id": "integer",
    "created_at": "datetime",
    "title": "string | null",
    "content": "string",
    "emotion_tags": "string | null"
}
```

### Usunięcie wpisu
```http
DELETE /api/diary/entries/{entry_id}
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "detail": "string"
}
```

### Lista tagów emocji
```http
GET /api/diary/emotion-tags
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "tags": [
        {
            "tag": "string",
            "count": "integer"
        }
    ]
}
```

## Walidacja

### Tytuł
- 1-200 znaków
- Opcjonalny
- Bez HTML i znaków kontrolnych

### Treść
- 1-5000 znaków
- Wymagana
- Bez HTML i znaków kontrolnych
- Bez nadmiarowych białych znaków

### Tagi emocji
- Rozdzielone przecinkami
- Maksymalnie 10 tagów
- 1-20 znaków na tag
- Bez duplikatów
- Bez HTML i znaków kontrolnych

## Cache

### Wpisy
- Cachowane przez 5 minut
- Klucze:
  - `diary:entry:{id}`
  - `diary:user:{user_id}:latest`
- Automatyczne odświeżanie przy edycji/usunięciu

### Tagi
- Cachowane przez 1 godzinę
- Klucz: `diary:tags:all`
- Odświeżane przy dodaniu/edycji wpisu

## Przykłady

### Dodanie wpisu
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.post(
    "/api/diary/entries",
    headers=headers,
    json={
        "title": "Mój dzień",
        "content": "Dziś czuję się...",
        "emotion_tags": "radość,spokój,wdzięczność"
    }
)
```

### Pobranie wpisów
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.get(
    "/api/diary/entries",
    headers=headers,
    params={
        "skip": 0,
        "limit": 10,
        "emotion_tag": "radość"
    }
)
```

### Edycja wpisu
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.put(
    f"/api/diary/entries/{entry_id}",
    headers=headers,
    json={
        "content": "Zaktualizowana treść...",
        "emotion_tags": "radość,spokój"
    }
)
```

### Usunięcie wpisu
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.delete(
    f"/api/diary/entries/{entry_id}",
    headers=headers
)
```

