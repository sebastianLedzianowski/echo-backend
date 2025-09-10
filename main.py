import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.routes import auth, users, admin, echo, stats, psychological_tests, prometheus_stats
from src.conf.config import settings
from src.services.metrics import instrumentator
from src.middleware import MetricsMiddleware

from dotenv import load_dotenv
load_dotenv()

# Konfiguracja logowania
logger = logging.getLogger(__name__)
# Nie konfigurujemy basic config, żeby uniknąć podwójnych logów
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)



# Konfiguracja root loggera
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("app")



# Middleware do obsługi błędów
class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Nieobsłużony błąd: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "Wystąpił wewnętrzny błąd serwera"}
            )


app = FastAPI(
    title="Echo Backend API",
    description="API dla platformy wsparcia emocjonalnego i filozoficznego",
    version="1.0.0",
    docs_url="/docs",  # Zmiana ścieżki dokumentacji
    redoc_url="/redoc"
)

# Lista dozwolonych hostów
allowed_hosts = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    settings.postgres_server,  # Host bazy danych
    settings.mail_server,  # Host serwera pocztowego
    "ollama",  # Serwis Ollama
    "testserver"
]

# Lista dozwolonych origins dla CORS
allowed_origins = [
    "http://localhost:8000",
    "http://localhost:3000",
    "http://localhost:8080",
    # Dodaj tutaj produkcyjne domeny
]

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=allowed_hosts
)

# Middleware do obsługi błędów
app.add_middleware(ErrorHandlingMiddleware)

# Metrics middleware
app.add_middleware(MetricsMiddleware)

# CORS middleware z ograniczonymi metodami i nagłówkami
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With"
    ]
)

# Statyczne pliki (opcjonalnie)
# app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router, prefix='/api')
app.include_router(users.router, prefix='/api')
app.include_router(admin.router, prefix='/api')
app.include_router(echo.router, prefix='/api')
app.include_router(psychological_tests.router, prefix='/api')

app.include_router(stats.router, prefix='/api')
app.include_router(prometheus_stats.router, prefix='/api')

# Instrument the app with Prometheus metrics
instrumentator.instrument(app).expose(app)

@app.get("/")
async def read_root():
    """
    Endpoint główny aplikacji.
    
    Returns:
        dict: Podstawowe informacje o API
    """
    return {
        "message": "Echo Backend API",
        "version": "1.0.0",
        "docs": "/docs",  # Zaktualizowane ścieżki
        "redoc": "/redoc",
        "status": "healthy",  # Status aplikacji
        "environment": "development" if __debug__ else "production"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)