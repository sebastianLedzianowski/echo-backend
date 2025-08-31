# Autentykacja i Autoryzacja

## Endpointy

### Rejestracja
```http
POST /api/auth/signup
```

**Request:**
```json
{
    "username": "string (5-55 znaków)",
    "password": "string (6-55 znaków)",
    "email": "string (opcjonalny)",
    "full_name": "string (opcjonalny)"
}
```

**Response:**
```json
{
    "user": {
        "id": "integer",
        "username": "string",
        "email": "string | null",
        "full_name": "string | null",
        "created_at": "datetime"
    },
    "detail": "string"
}
```

### Logowanie
```http
POST /api/auth/login
```

**Request:**
```json
{
    "username": "string",
    "password": "string"
}
```

**Response:**
```json
{
    "access_token": "string",
    "refresh_token": "string",
    "token_type": "bearer"
}
```

### Odświeżenie tokenu
```http
GET /api/auth/refresh_token
```

**Headers:**
```
Authorization: Bearer <refresh_token>
```

**Response:**
```json
{
    "access_token": "string",
    "refresh_token": "string",
    "token_type": "bearer"
}
```

### Potwierdzenie email
```http
GET /api/auth/confirmed_email/{token}
```

**Response:**
```json
{
    "message": "string"
}
```

### Prośba o ponowne wysłanie maila
```http
POST /api/auth/request_email
```

**Request:**
```json
{
    "email": "string"
}
```

**Response:**
```json
{
    "message": "string"
}
```

### Reset hasła - żądanie
```http
POST /api/auth/request_password_reset
```

**Request:**
```json
{
    "email": "string"
}
```

**Response:**
```json
{
    "message": "string"
}
```

### Reset hasła - ustawienie nowego
```http
POST /api/auth/reset_password
```

**Request:**
```json
{
    "token": "string",
    "new_password": "string"
}
```

**Response:**
```json
{
    "message": "string"
}
```

## Walidacja

### Hasło
- Minimum 6 znaków
- Maksimum 55 znaków
- Przynajmniej 1 wielka litera
- Przynajmniej 1 mała litera
- Przynajmniej 1 cyfra
- Przynajmniej 1 znak specjalny

### Nazwa użytkownika
- 5-55 znaków
- Tylko litery, cyfry i podkreślenia
- Musi zaczynać się od litery
- Bez kolejnych podkreśleń
- Unikalna w systemie

### Email
- Poprawny format email
- Unikalny w systemie
- Opcjonalny przy rejestracji
- Wymagane potwierdzenie przed użyciem

## Tokeny

### Access Token
- Ważny przez 15 minut
- Używany do autoryzacji requestów
- Zawiera: username, scope, iat, exp

### Refresh Token
- Ważny przez 7 dni
- Używany do odświeżania access tokena
- Przechowywany w bazie danych
- Unieważniany przy wylogowaniu

## Bezpieczeństwo

### Hasła
- Hashowane przy użyciu bcrypt
- Nigdy nie przechowywane w czystym tekście
- Minimalne wymagania siły hasła

### Tokeny
- Podpisane kluczem serwera
- Krótki czas życia access tokena
- Możliwość unieważnienia refresh tokena
- Weryfikacja scope

### Sesje
- Bezstanowe (JWT)
- Możliwość wylogowania ze wszystkich urządzeń
- Rate limiting na endpointach auth
- Blokada konta po zbyt wielu próbach

## Przykłady

### Rejestracja i logowanie
```python
# Rejestracja
response = await client.post("/api/auth/signup", json={
    "username": "testuser",
    "password": "StrongPass1!",
    "email": "test@example.com"
})

# Logowanie
response = await client.post("/api/auth/login", json={
    "username": "testuser",
    "password": "StrongPass1!"
})

# Użycie tokena
headers = {
    "Authorization": f"Bearer {response.json()['access_token']}"
}
response = await client.get("/api/users/me", headers=headers)
```

### Odświeżanie tokena
```python
response = await client.get(
    "/api/auth/refresh_token",
    headers={"Authorization": f"Bearer {refresh_token}"}
)
```

### Reset hasła
```python
# Żądanie resetu
response = await client.post("/api/auth/request_password_reset", json={
    "email": "test@example.com"
})

# Ustawienie nowego hasła
response = await client.post("/api/auth/reset_password", json={
    "token": "reset_token",
    "new_password": "NewStrongPass1!"
})
```

