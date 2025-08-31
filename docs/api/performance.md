# Wydajność

## Baza danych

### Indeksy
```sql
-- Użytkownicy
CREATE INDEX ix_users_username ON users(username);
CREATE INDEX ix_users_email ON users(email);
CREATE INDEX ix_users_created_at ON users(created_at);
CREATE INDEX ix_users_is_active ON users(is_active);
CREATE INDEX ix_users_is_admin ON users(is_admin);

-- Dziennik
CREATE INDEX ix_diary_entries_user_id ON diary_entries(user_id);
CREATE INDEX ix_diary_entries_created_at ON diary_entries(created_at);
CREATE INDEX ix_diary_entries_emotion_tags ON diary_entries(emotion_tags);

-- Konwersacje
CREATE INDEX ix_conversation_history_user_id ON conversation_history(user_id);
CREATE INDEX ix_conversation_history_mode ON conversation_history(mode);
CREATE INDEX ix_conversation_history_created_at ON conversation_history(created_at);
CREATE INDEX ix_conversation_history_user_mode ON conversation_history(user_id, mode);
```

### Optymalizacja zapytań
```python
# Eager loading
query = (
    db.query(User)
    .options(
        selectinload(User.diary_entries),
        selectinload(User.conversation_history)
    )
)

# Paginacja
query = (
    db.query(DiaryEntry)
    .filter(DiaryEntry.user_id == user_id)
    .order_by(DiaryEntry.created_at.desc())
    .offset(skip)
    .limit(limit)
)

# Agregacja
query = (
    db.query(
        func.date(DiaryEntry.created_at),
        func.count(DiaryEntry.id)
    )
    .group_by(func.date(DiaryEntry.created_at))
)
```

## Cache

### Konfiguracja Redis
```python
REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'encoding': 'utf-8',
    'decode_responses': True,
    'socket_timeout': 5,
    'socket_connect_timeout': 5,
    'retry_on_timeout': True,
    'health_check_interval': 30
}
```

### Strategie cachowania
```python
# Użytkownicy (30 minut)
await cache.set(
    f"user:id:{user.id}",
    user.dict(),
    expire=timedelta(minutes=30)
)

# Odpowiedzi AI (1 godzina)
await cache.set(
    f"ai:response:{response_hash}",
    response,
    expire=timedelta(hours=1)
)

# Statystyki (5 minut)
await cache.set(
    "stats:overview",
    stats,
    expire=timedelta(minutes=5)
)
```

### Invalidacja
```python
# Pojedynczy klucz
await cache.delete(f"user:id:{user_id}")

# Wzorzec
await cache.delete_pattern(f"user:*:{user_id}")

# Wszystko
await cache.flush_all()
```

## Asynchroniczność

### FastAPI
```python
@router.get("/users")
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    # Asynchroniczne operacje
    users = await get_users_async(skip, limit, db)
    stats = await get_stats_async(db)
    
    return {
        "users": users,
        "stats": stats
    }
```

### Zadania w tle
```python
@router.post("/signup")
async def signup(
    user: UserCreate,
    background_tasks: BackgroundTasks
):
    # Główna operacja
    new_user = await create_user(user)
    
    # Zadania w tle
    background_tasks.add_task(send_welcome_email, new_user)
    background_tasks.add_task(update_stats)
    
    return new_user
```

## Optymalizacja kodu

### Pula połączeń
```python
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600
)
```

### Współbieżność
```python
async def process_batch(items: List[Any]):
    tasks = [
        process_item(item)
        for item in items
    ]
    return await asyncio.gather(*tasks)
```

### Buforowanie
```python
class ResponseBuffer:
    def __init__(self, max_size: int = 1000):
        self.buffer = []
        self.max_size = max_size
    
    async def add(self, item: Any):
        self.buffer.append(item)
        if len(self.buffer) >= self.max_size:
            await self.flush()
    
    async def flush(self):
        if self.buffer:
            await process_batch(self.buffer)
            self.buffer.clear()
```

## Monitorowanie wydajności

### Metryki
```python
# Czas odpowiedzi
RESPONSE_TIME = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

# Użycie pamięci
MEMORY_USAGE = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes'
)

# Cache hit rate
CACHE_HITS = Counter(
    'cache_hits_total',
    'Total number of cache hits'
)
```

### Profilowanie
```python
@profile
async def generate_response(text: str) -> str:
    # Kod do profilowania
    pass

def profile(func):
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        
        logger.info(
            f"{func.__name__} took {duration:.2f}s",
            extra={
                "function": func.__name__,
                "duration": duration,
                "args": args,
                "kwargs": kwargs
            }
        )
        
        return result
    return wrapper
```

## Optymalizacja zasobów

### Kompresja
```python
app.add_middleware(
    GZipMiddleware,
    minimum_size=1000
)
```

### Limity
```python
class Settings(BaseSettings):
    MAX_CONTENT_LENGTH: int = 1024 * 1024  # 1MB
    MAX_CONNECTIONS: int = 100
    RATE_LIMIT: int = 60  # req/min
    TIMEOUT: int = 30  # seconds
```

### Czyszczenie
```python
async def cleanup_old_data():
    """Usuwa stare dane."""
    # Konwersacje starsze niż 30 dni
    await db.execute(
        delete(ConversationHistory)
        .where(
            ConversationHistory.created_at <
            datetime.utcnow() - timedelta(days=30)
        )
    )
    
    # Nieużywane tokeny
    await db.execute(
        delete(User)
        .where(
            User.refresh_token.isnot(None),
            User.last_login <
            datetime.utcnow() - timedelta(days=7)
        )
    )
```

## Dobre praktyki

### Baza danych
- Używaj indeksów
- Optymalizuj zapytania
- Używaj paginacji
- Monitoruj wydajność
- Regularnie czyść

### Cache
- Cachuj często używane
- Ustaw rozsądne TTL
- Monitoruj hit rate
- Planuj invalidację
- Używaj wzorców

### Kod
- Profiluj kod
- Używaj asynchroniczności
- Optymalizuj pętle
- Buforuj operacje
- Monitoruj pamięć

### Infrastruktura
- Skaluj horyzontalnie
- Używaj load balancera
- Monitoruj zasoby
- Ustaw limity
- Planuj pojemność

