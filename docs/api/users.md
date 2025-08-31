# Zarządzanie Użytkownikami

## Endpointy

### Profil użytkownika
```http
GET /api/users/me
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "id": "integer",
    "username": "string",
    "email": "string | null",
    "full_name": "string | null",
    "created_at": "datetime"
}
```

### Aktualizacja profilu
```http
PATCH /api/users/me
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "full_name": "string (opcjonalny)",
    "email": "string (opcjonalny)"
}
```

**Response:**
```json
{
    "id": "integer",
    "username": "string",
    "email": "string | null",
    "full_name": "string | null",
    "created_at": "datetime"
}
```

### Zmiana hasła
```http
PATCH /api/users/me/password
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "old_password": "string",
    "new_password": "string"
}
```

**Response:**
```json
{
    "detail": "string"
}
```

### Usunięcie konta
```http
DELETE /api/users/me
```

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
    "password": "string"
}
```

**Response:**
```json
{
    "detail": "string"
}
```

## Walidacja

### Pełna nazwa
- 5-64 znaków
- Może zawierać litery, cyfry, spacje i myślniki
- Opcjonalna

### Email
- Poprawny format email
- Unikalny w systemie
- Wymaga potwierdzenia po zmianie
- Opcjonalny

### Hasło (przy zmianie)
- Minimum 6 znaków
- Maksimum 55 znaków
- Przynajmniej 1 wielka litera
- Przynajmniej 1 mała litera
- Przynajmniej 1 cyfra
- Przynajmniej 1 znak specjalny
- Nie może być takie samo jak stare

## Cache

### Dane użytkownika
- Cachowane przez 30 minut
- Klucze:
  - `user:id:{id}`
  - `user:username:{username}`
  - `user:email:{email}`
- Automatyczne odświeżanie przy aktualizacji
- Czyszczenie przy usunięciu konta

## Przykłady

### Pobranie profilu
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.get("/api/users/me", headers=headers)
```

### Aktualizacja profilu
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.patch(
    "/api/users/me",
    headers=headers,
    json={
        "full_name": "Jan Kowalski",
        "email": "jan@example.com"
    }
)
```

### Zmiana hasła
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.patch(
    "/api/users/me/password",
    headers=headers,
    json={
        "old_password": "OldPass1!",
        "new_password": "NewPass1!"
    }
)
```

### Usunięcie konta
```python
headers = {"Authorization": f"Bearer {access_token}"}
response = await client.delete(
    "/api/users/me",
    headers=headers,
    json={"password": "CurrentPass1!"}
)
```

