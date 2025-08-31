# Bezpieczeństwo

## Uwierzytelnianie

### JWT
- Access token (15 minut)
- Refresh token (7 dni)
- Podpisane kluczem serwera
- Weryfikacja scope
- Możliwość unieważnienia

### Hasła
- Hashowane (bcrypt)
- Minimalne wymagania:
  - 6+ znaków
  - Wielka litera
  - Mała litera
  - Cyfra
  - Znak specjalny
- Blokada po nieudanych próbach
- Wymuszona zmiana co 90 dni

### Sesje
- Bezstanowe (JWT)
- Refresh token w bazie
- Możliwość wylogowania ze wszystkich urządzeń
- Automatyczne czyszczenie starych tokenów

## CORS

### Konfiguracja
```python
origins = [
    "http://localhost:8000",
    "http://localhost:3000",
    "http://localhost:8080"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

### Zabezpieczenia
- Ograniczone origins
- Weryfikacja credentials
- Kontrola metod HTTP
- Kontrola nagłówków
- Preflight requests

## Rate Limiting

### Limity
- 60 requestów/minutę/IP
- 1000 requestów/godzinę/użytkownik
- 10 prób logowania/godzinę/IP
- 100 requestów AI/godzinę/użytkownik
- 1000 requestów/godzinę/admin

### Implementacja
```python
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    path = request.url.path
    
    # Sprawdź limit
    if not rate_limiter.allow(client_ip, path):
        raise HTTPException(
            status_code=429,
            detail="Too many requests"
        )
    
    return await call_next(request)
```

## Walidacja danych

### Wejście
- Sanityzacja HTML
- Walidacja typów
- Limity długości
- Format danych
- Białe listy

### Wyjście
- Enkodowanie HTML
- Filtrowanie danych wrażliwych
- Kontrola typów
- Walidacja schematów
- Limity odpowiedzi

## Headers bezpieczeństwa

```python
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    return response
```

## Szyfrowanie

### W spoczynku
- Hasła (bcrypt)
- Tokeny (JWT)
- Dane wrażliwe (AES-256)
- Klucze (RSA)
- Backupy (GPG)

### W transporcie
- HTTPS/TLS 1.3
- Certyfikaty SSL
- Perfect Forward Secrecy
- HSTS
- Certificate Pinning

## Audyt

### Logowanie
- Logowania/wylogowania
- Zmiany uprawnień
- Operacje admina
- Błędy bezpieczeństwa
- Podejrzana aktywność

### Format
```python
{
    "timestamp": "ISO8601",
    "event_type": "string",
    "user_id": "integer|null",
    "ip_address": "string",
    "user_agent": "string",
    "details": {
        "action": "string",
        "target": "string",
        "status": "string",
        "changes": "object"
    }
}
```

## Przykłady

### Walidacja hasła
```python
def validate_password(password: str) -> bool:
    if len(password) < 6:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    if not any(not c.isalnum() for c in password):
        return False
    return True
```

### Rate limiting
```python
class RateLimiter:
    def __init__(self, redis):
        self.redis = redis
    
    async def allow(
        self,
        key: str,
        limit: int,
        window: int
    ) -> bool:
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, window)
        return current <= limit
```

### Audyt logowania
```python
async def log_login_attempt(
    request: Request,
    success: bool,
    user_id: Optional[int] = None
):
    await audit_logger.info(
        "login_attempt",
        {
            "success": success,
            "user_id": user_id,
            "ip": request.client.host,
            "user_agent": request.headers.get("User-Agent")
        }
    )
```

## Checklist bezpieczeństwa

### Uwierzytelnianie
- [ ] Silne hasła
- [ ] Bezpieczne tokeny
- [ ] Limity prób
- [ ] 2FA (opcjonalnie)
- [ ] Bezpieczne resety hasła

### Autoryzacja
- [ ] RBAC
- [ ] Granularne uprawnienia
- [ ] Walidacja dostępu
- [ ] Separacja ról
- [ ] Audyt zmian

### Dane
- [ ] Walidacja wejścia
- [ ] Sanityzacja wyjścia
- [ ] Szyfrowanie wrażliwych
- [ ] Bezpieczne usuwanie
- [ ] Kopie zapasowe

### Infrastruktura
- [ ] HTTPS
- [ ] Firewall
- [ ] Rate limiting
- [ ] Monitoring
- [ ] Aktualizacje

### Kod
- [ ] Code review
- [ ] Testy bezpieczeństwa
- [ ] Dependency scanning
- [ ] Static analysis
- [ ] Security headers

## Reagowanie na incydenty

### Plan
1. Wykrycie
2. Ocena
3. Powstrzymanie
4. Usunięcie
5. Odzyskanie
6. Analiza

### Procedury
- Blokada konta
- Reset tokenów
- Backup danych
- Powiadomienie użytkowników
- Raport incydentu

### Kontakty
- Administrator systemu
- Zespół bezpieczeństwa
- Pomoc techniczna
- Prawnik
- CERT

