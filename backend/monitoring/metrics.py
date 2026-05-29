import time
from prometheus_client import Counter, Histogram


# Celery task metrics
CELERY_TASK_DURATION = Histogram(
    'celery_task_duration_seconds',
    'Duration of Celery tasks in seconds',
    ['task_name', 'status'],
)
CELERY_TASK_COUNTER = Counter(
    'celery_task_executions_total',
    'Total Celery task executions',
    ['task_name', 'status'],
)


# Cache metrics
CACHE_HIT_COUNTER = Counter('cache_hits_total', 'Cache hits')
CACHE_MISS_COUNTER = Counter('cache_misses_total', 'Cache misses')


# HTTP request metrics
REQUEST_LATENCY = Histogram(
    'django_http_request_duration_seconds',
    'Django request latency in seconds',
    ['method', 'path', 'status_code'],
)


def safe_label_path(path: str) -> str:
    # Keep labels short and stable: use first 64 chars
    return (path or '/')[:64]
