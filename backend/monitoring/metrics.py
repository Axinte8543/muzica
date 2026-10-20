import time

try:
    from prometheus_client import Counter, Histogram
    PROMETHEUS_AVAILABLE = True
except Exception:
    PROMETHEUS_AVAILABLE = False

    class _NullMetric:
        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            return None

        def observe(self, *args, **kwargs):
            return None

    class Counter:                          
        def __new__(cls, *args, **kwargs):
            return _NullMetric()

    class Histogram:                          
        def __new__(cls, *args, **kwargs):
            return _NullMetric()


                     
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


               
CACHE_HIT_COUNTER = Counter('cache_hits_total', 'Cache hits')
CACHE_MISS_COUNTER = Counter('cache_misses_total', 'Cache misses')


                      
REQUEST_LATENCY = Histogram(
    'django_http_request_duration_seconds',
    'Django request latency in seconds',
    ['method', 'path', 'status_code'],
)


def safe_label_path(path: str) -> str:
                                                      
    return (path or '/')[:64]
