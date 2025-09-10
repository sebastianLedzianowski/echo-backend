"""
Metrics middleware for automatic collection of API metrics
"""
import time
import psutil
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.services.metrics import (
    record_api_request,
    record_error,
    update_memory_usage,
    update_cpu_usage,
    record_db_query
)

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting API metrics"""

    def __init__(self, app, exclude_paths: list = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/metrics", "/health", "/docs", "/redoc", "/openapi.json"
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics collection for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        start_time = time.time()
        method = request.method
        endpoint = request.url.path

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Record API metrics
            record_api_request(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
                duration=duration
            )

            # Update system metrics
            self._update_system_metrics()

            return response

        except Exception as e:
            # Calculate duration even for errors
            duration = time.time() - start_time

            # Record error metrics
            error_type = type(e).__name__
            record_error(error_type=error_type, endpoint=endpoint)

            # Record API metrics for error
            record_api_request(
                method=method,
                endpoint=endpoint,
                status_code=500,
                duration=duration
            )

            # Update system metrics
            self._update_system_metrics()

            # Re-raise the exception
            raise
    
    def _update_system_metrics(self):
        """Update system metrics"""
        try:
            # Memory usage
            memory_info = psutil.virtual_memory()
            update_memory_usage(memory_info.used)

            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=None)
            update_cpu_usage(cpu_percent)

        except Exception as e:
            logger.warning(f"Failed to update system metrics: {e}")


class DatabaseMetricsMiddleware:
    """Context manager for database query metrics"""

    def __init__(self, operation: str):
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            record_db_query(self.operation, duration)


# Decorator for database operations
def track_db_operation(operation: str):
    """Decorator to track database operations"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with DatabaseMetricsMiddleware(operation):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


# Context manager for LLM operations
class LLMMetricsContext:
    """Context manager for LLM metrics"""

    def __init__(self, model: str, endpoint: str):
        self.model = model
        self.endpoint = endpoint
        self.start_time = None
        self.status = "success"
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.cost_usd = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time

            # Determine status
            if exc_type is not None:
                self.status = "error"

            # Record metrics
            from src.services.metrics import record_llm_request
            record_llm_request(
                model=self.model,
                endpoint=self.endpoint,
                status=self.status,
                duration=duration,
                prompt_tokens=self.prompt_tokens,
                completion_tokens=self.completion_tokens,
                total_tokens=self.total_tokens,
                cost_usd=self.cost_usd
            )

    def set_tokens(
        self, prompt_tokens: int = 0, completion_tokens: int = 0,
        total_tokens: int = 0, cost_usd: float = 0.0
    ):
        """Set token and cost information"""
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.cost_usd = cost_usd
