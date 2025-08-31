# Monitoring i Metryki

## Logowanie

### Struktura logów
```
logs/
├── app_YYYYMMDD.log     # Logi aplikacji
├── error_YYYYMMDD.log   # Błędy
└── access_YYYYMMDD.log  # Logi dostępu
```

### Format logów
```python
{
    "timestamp": "ISO8601",
    "level": "INFO|WARNING|ERROR|CRITICAL",
    "logger": "string",
    "message": "string",
    "extra": {
        "request_id": "string",
        "user_id": "integer|null",
        "path": "string",
        "method": "string",
        "status_code": "integer",
        "duration_ms": "float"
    }
}
```

### Poziomy logowania
- DEBUG: Szczegółowe informacje (tylko dev)
- INFO: Standardowe operacje
- WARNING: Problemy nieblokujące
- ERROR: Błędy wymagające uwagi
- CRITICAL: Błędy krytyczne

## Metryki

### HTTP
- Liczba requestów
- Czas odpowiedzi
- Kody odpowiedzi
- Aktywni użytkownicy
- Rozmiar odpowiedzi

### Baza danych
- Liczba zapytań
- Czas wykonania
- Liczba połączeń
- Wykorzystanie pamięci
- Obciążenie CPU

### Cache
- Hit rate
- Miss rate
- Eviction rate
- Wykorzystanie pamięci
- Liczba kluczy

### AI
- Czas generowania
- Długość odpowiedzi
- Użycie tokenów
- Błędy generowania
- Cache hit rate

## Alerty

### Krytyczne
- Czas odpowiedzi > 5s
- Błędy 5xx > 1%
- Wykorzystanie CPU > 80%
- Wykorzystanie RAM > 80%
- Niedostępność Redis/DB

### Ważne
- Czas odpowiedzi > 2s
- Błędy 4xx > 5%
- Wykorzystanie CPU > 60%
- Wykorzystanie RAM > 60%
- Cache miss rate > 50%

### Informacyjne
- Nowi użytkownicy
- Aktywność użytkowników
- Wykorzystanie AI
- Zmiany w cache
- Długie operacje

## Dashboard

### Ogólne
- Status systemu
- Liczba użytkowników
- Liczba requestów
- Błędy
- Wydajność

### Użytkownicy
- Aktywni użytkownicy
- Nowe rejestracje
- Logowania
- Konwersje
- Retencja

### Wydajność
- Czas odpowiedzi
- Użycie zasobów
- Cache hit rate
- Błędy
- Latencja

### AI
- Generowane odpowiedzi
- Czas generowania
- Użycie cache
- Błędy
- Popularne tematy

## Narzędzia

### Prometheus
```yaml
scrape_configs:
  - job_name: 'echo_backend'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
```

### Grafana
```yaml
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
```

### ELK Stack
```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /app/logs/*.log
  json.keys_under_root: true
```

## Przykłady

### Logowanie requestu
```python
logger.info(
    "HTTP Request",
    extra={
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "user_id": current_user.id if current_user else None,
        "duration_ms": duration * 1000
    }
)
```

### Metryka czasu odpowiedzi
```python
RESPONSE_TIME = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

@RESPONSE_TIME.time()
async def handle_request():
    # ...
```

### Alert na błędy
```python
def check_error_rate(errors, total):
    rate = errors / total
    if rate > 0.01:  # 1%
        alert_critical("High error rate", {
            "error_rate": rate,
            "errors": errors,
            "total": total
        })
```

## Monitorowanie wydajności

### Profilowanie
```python
@profile
async def generate_response(text: str) -> str:
    # ...
```

### Tracing
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("generate_ai_response")
async def generate_ai_response():
    # ...
```

### Metryki pamięci
```python
def monitor_memory():
    process = psutil.Process()
    return {
        "rss": process.memory_info().rss,
        "vms": process.memory_info().vms,
        "percent": process.memory_percent()
    }
```

## Eksport danych

### Prometheus
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",status="200"} 1234

# HELP http_request_duration_seconds HTTP request duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1"} 1000
```

### Grafana Dashboard
```json
{
  "panels": [
    {
      "title": "HTTP Requests",
      "type": "graph",
      "datasource": "Prometheus",
      "targets": [
        {
          "expr": "rate(http_requests_total[5m])"
        }
      ]
    }
  ]
}
```

### Alert Rules
```yaml
groups:
  - name: echo_backend
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: High error rate detected
```

