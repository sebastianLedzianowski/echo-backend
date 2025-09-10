"""
Prometheus metrics service for Echo Backend
"""
from typing import Optional
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_fastapi_instrumentator.metrics import Info

# Custom metrics registry
registry = CollectorRegistry()

# API Metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status_code'],
    registry=registry
)

api_request_duration_seconds = Histogram(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    registry=registry
)

# User Metrics
active_users = Gauge(
    'active_users_total',
    'Number of active users',
    registry=registry
)

user_registrations_total = Counter(
    'user_registrations_total',
    'Total number of user registrations',
    ['status'],
    registry=registry
)

# AI/LLM Metrics
llm_requests_total = Counter(
    'llm_requests_total',
    'Total number of LLM requests',
    ['model', 'endpoint', 'status'],
    registry=registry
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM request duration in seconds',
    ['model', 'endpoint'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
    registry=registry
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total number of tokens processed',
    ['model', 'token_type'],
    registry=registry
)

llm_cost_usd_total = Counter(
    'llm_cost_usd_total',
    'Total cost of LLM requests in USD',
    ['model'],
    registry=registry
)

# Conversation Metrics
conversations_total = Counter(
    'conversations_total',
    'Total number of conversations',
    ['mode', 'user_type'],
    registry=registry
)

diary_entries_total = Counter(
    'diary_entries_total',
    'Total number of diary entries',
    registry=registry
)

# Psychological Tests Metrics
psychological_tests_total = Counter(
    'psychological_tests_total',
    'Total number of psychological tests',
    ['test_type', 'status'],
    registry=registry
)

test_scores = Histogram(
    'psychological_test_scores',
    'Distribution of psychological test scores',
    ['test_type'],
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
    registry=registry
)

# Database Metrics
db_connections_active = Gauge(
    'db_connections_active',
    'Number of active database connections',
    registry=registry
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=registry
)

# System Metrics
memory_usage_bytes = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes',
    registry=registry
)

cpu_usage_percent = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage',
    registry=registry
)

# Error Metrics
errors_total = Counter(
    'errors_total',
    'Total number of errors',
    ['error_type', 'endpoint'],
    registry=registry
)

# Custom metrics functions
def record_api_request(
    method: str, endpoint: str, status_code: int, duration: float
):
    """Record API request metrics"""
    api_requests_total.labels(
        method=method, endpoint=endpoint, status_code=status_code
    ).inc()
    api_request_duration_seconds.labels(
        method=method, endpoint=endpoint
    ).observe(duration)

def record_llm_request(
    model: str, endpoint: str, status: str, duration: float,
    prompt_tokens: int = 0, completion_tokens: int = 0,
    total_tokens: int = 0, cost_usd: float = 0.0
):
    """Record LLM request metrics"""
    llm_requests_total.labels(
        model=model, endpoint=endpoint, status=status
    ).inc()
    llm_request_duration_seconds.labels(
        model=model, endpoint=endpoint
    ).observe(duration)

    if prompt_tokens > 0:
        llm_tokens_total.labels(
            model=model, token_type='prompt'
        ).inc(prompt_tokens)
    if completion_tokens > 0:
        llm_tokens_total.labels(
            model=model, token_type='completion'
        ).inc(completion_tokens)
    if total_tokens > 0:
        llm_tokens_total.labels(
            model=model, token_type='total'
        ).inc(total_tokens)
    if cost_usd > 0:
        llm_cost_usd_total.labels(model=model).inc(cost_usd)

def record_conversation(mode: str, user_type: str = 'authenticated'):
    """Record conversation metrics"""
    conversations_total.labels(mode=mode, user_type=user_type).inc()


def record_diary_entry():
    """Record diary entry metrics"""
    diary_entries_total.inc()


def record_psychological_test(
    test_type: str, status: str, score: Optional[float] = None
):
    """Record psychological test metrics"""
    psychological_tests_total.labels(
        test_type=test_type, status=status
    ).inc()
    if score is not None:
        test_scores.labels(test_type=test_type).observe(score)


def record_user_registration(status: str):
    """Record user registration metrics"""
    user_registrations_total.labels(status=status).inc()


def record_error(error_type: str, endpoint: str):
    """Record error metrics"""
    errors_total.labels(error_type=error_type, endpoint=endpoint).inc()


def record_db_query(operation: str, duration: float):
    """Record database query metrics"""
    db_query_duration_seconds.labels(operation=operation).observe(duration)


def update_active_users(count: int):
    """Update active users count"""
    active_users.set(count)


def update_memory_usage(bytes_used: int):
    """Update memory usage"""
    memory_usage_bytes.set(bytes_used)


def update_cpu_usage(percent: float):
    """Update CPU usage"""
    cpu_usage_percent.set(percent)


def update_db_connections(count: int):
    """Update database connections count"""
    db_connections_active.set(count)


# Custom instrumentator with additional metrics
def create_custom_metrics():
    """Create custom metrics for the instrumentator"""

    def latency_metric(info: Info) -> str:
        """Custom latency metric"""
        return (f"custom_latency_seconds{info.modified_handler} "
                f"{info.modified_duration}")

    def request_size_metric(info: Info) -> str:
        """Custom request size metric"""
        if (hasattr(info.request, 'content_length') and
                info.request.content_length):
            return (f"custom_request_size_bytes{info.modified_handler} "
                    f"{info.request.content_length}")
        return ""

    def response_size_metric(info: Info) -> str:
        """Custom response size metric"""
        if (hasattr(info.response, 'content_length') and
                info.response.content_length):
            return (f"custom_response_size_bytes{info.modified_handler} "
                    f"{info.response.content_length}")
        return ""

    return [
        latency_metric,
        request_size_metric,
        response_size_metric,
    ]


# Create instrumentator instance
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics", "/health"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="api_requests_inprogress",
    inprogress_labels=True
)

# Add default metrics
instrumentator.add(metrics.default())

# Add custom metrics
instrumentator.add(
    metrics.latency(
        should_include_handler=True,
        should_include_method=True,
        should_include_status=True,
        metric_namespace="echo_backend",
        metric_subsystem="api"
    )
)

instrumentator.add(
    metrics.requests(
        should_include_handler=True,
        should_include_method=True,
        should_include_status=True,
        metric_namespace="echo_backend",
        metric_subsystem="api"
    )
)

instrumentator.add(
    metrics.request_size(
        should_include_handler=True,
        should_include_method=True,
        metric_namespace="echo_backend",
        metric_subsystem="api"
    )
)

instrumentator.add(
    metrics.response_size(
        should_include_handler=True,
        should_include_method=True,
        metric_namespace="echo_backend",
        metric_subsystem="api"
    )
)
