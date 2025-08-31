# Panel Administratora

## Endpointy

### Przegląd systemu
```http
GET /api/admin/dashboard/overview
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "users": {
        "total": "integer",
        "active": "integer",
        "confirmed": "integer",
        "admins": "integer",
        "new_24h": "integer"
    },
    "diary": {
        "total_entries": "integer",
        "recent_7_days": "integer",
        "new_24h": "integer"
    },
    "conversations": {
        "total": "integer",
        "recent_7_days": "integer",
        "new_24h": "integer"
    },
    "redis": {
        "connected": "boolean",
        "keys": "integer",
        "memory": "string",
        "clients": "integer"
    },
    "system": {
        "timestamp": "datetime",
        "redis_connected": "boolean"
    }
}
```

### Statystyki użytkowników
```http
GET /api/admin/dashboard/users/stats
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "users_by_status": [
        {
            "is_active": "boolean",
            "is_confirmed": "boolean",
            "count": "integer"
        }
    ],
    "registrations_by_day": [
        {
            "date": "string",
            "count": "integer"
        }
    ],
    "top_active_users": [
        {
            "username": "string",
            "email": "string",
            "diary_count": "integer",
            "conversation_count": "integer"
        }
    ]
}
```

### Statystyki dziennika
```http
GET /api/admin/dashboard/diary/stats
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "entries_by_day": [
        {
            "date": "string",
            "count": "integer"
        }
    ],
    "entries_by_user": [
        {
            "username": "string",
            "entry_count": "integer"
        }
    ],
    "emotion_tags": {
        "total_tags": "integer",
        "unique_tags": "integer",
        "top_tags": [
            {
                "tag": "string",
                "count": "integer"
            }
        ]
    }
}
```

### Statystyki konwersacji
```http
GET /api/admin/dashboard/conversations/stats
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "conversations_by_mode": [
        {
            "mode": "string",
            "count": "integer"
        }
    ],
    "conversations_by_day": [
        {
            "date": "string",
            "count": "integer"
        }
    ],
    "conversations_by_user": [
        {
            "username": "string",
            "conversation_count": "integer"
        }
    ],
    "message_distribution": {
        "user_messages": "integer",
        "ai_messages": "integer",
        "total_messages": "integer"
    }
}
```

### Informacje Redis
```http
GET /api/admin/dashboard/redis/info
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "server": {
        "version": "string",
        "uptime": "integer",
        "connected_clients": "integer"
    },
    "memory": {
        "used": "string",
        "peak": "string",
        "fragmentation": "float"
    },
    "stats": {
        "total_connections": "integer",
        "total_commands": "integer",
        "ops_per_sec": "integer",
        "hit_rate": "float"
    },
    "keyspace": {
        "total_keys": "integer",
        "expires": "integer",
        "avg_ttl": "integer"
    }
}
```

### Stan systemu
```http
GET /api/admin/dashboard/system/health
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "timestamp": "datetime",
    "redis": {
        "connected": "boolean",
        "info": "object | null"
    },
    "database": {
        "status": "string"
    },
    "overall_status": "string"
}
```

## Cache

### Statystyki
- Cachowane przez 5 minut
- Klucze:
  - `admin:stats:overview`
  - `admin:stats:users`
  - `admin:stats:diary`
  - `admin:stats:conversations`
- Automatyczne odświeżanie przy zmianach

### Redis Info
- Cachowane przez 1 minutę
- Klucz: `admin:redis:info`
- Odświeżane przy każdym żądaniu

### Stan systemu
- Cachowane przez 30 sekund
- Klucz: `admin:system:health`
- Odświeżane przy każdym żądaniu

## Przykłady

### Pobranie przeglądu
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.get(
    "/api/admin/dashboard/overview",
    headers=headers
)
```

### Pobranie statystyk użytkowników
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.get(
    "/api/admin/dashboard/users/stats",
    headers=headers
)
```

### Pobranie stanu systemu
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.get(
    "/api/admin/dashboard/system/health",
    headers=headers
)
```

## Uprawnienia

### Wymagania
- Token z uprawnieniami admina
- Aktywne konto
- Potwierdzone konto

### Ograniczenia
- Brak możliwości modyfikacji danych
- Tylko odczyt statystyk i metryk
- Rate limiting: 600 requestów na godzinę

## Monitorowanie

### Metryki
- Liczba requestów admina
- Czas odpowiedzi endpointów
- Użycie zasobów
- Błędy i wyjątki

### Alerty
- Wysoki czas odpowiedzi
- Błędy krytyczne
- Problemy z Redis
- Problemy z bazą danych

