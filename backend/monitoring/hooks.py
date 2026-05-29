import time
import logging
from django.core.cache import cache

from prometheus_client import CollectorRegistry

from . import metrics


def _wrap_cache_get():
    try:
        orig_get = cache.get

        def wrapped_get(key, default=None, version=None):
            try:
                val = orig_get(key, default=default, version=version)
                if val is None:
                    metrics.CACHE_MISS_COUNTER.inc()
                else:
                    metrics.CACHE_HIT_COUNTER.inc()
                return val
            except Exception:
                # Don't let metrics break application behavior
                logging.exception('Cache get wrapper failed')
                return orig_get(key, default=default, version=version)

        cache.get = wrapped_get
    except Exception:
        logging.exception('Failed to wrap cache.get for metrics')


def _register_celery_signals():
    try:
        # Register Celery signal handlers if Celery is installed at runtime
        from celery import signals

        @signals.task_prerun.connect
        def _task_prerun(sender=None, task_id=None, task=None, *args, **kwargs):
            # store start time on the task object
            try:
                setattr(task, '__prom_start_time__', time.time())
            except Exception:
                pass

        @signals.task_postrun.connect
        def _task_postrun(sender=None, task_id=None, task=None, retval=None, state=None, **kwargs):
            try:
                start = getattr(task, '__prom_start_time__', None)
                task_name = getattr(sender, 'name', str(sender))
                if start:
                    duration = time.time() - start
                    metrics.CELERY_TASK_DURATION.labels(task_name=task_name, status='success').observe(duration)
                    metrics.CELERY_TASK_COUNTER.labels(task_name=task_name, status='success').inc()
                else:
                    # Count it anyway
                    metrics.CELERY_TASK_COUNTER.labels(task_name=task_name, status='success').inc()
            except Exception:
                logging.exception('Failed to record task_postrun metrics')

        @signals.task_failure.connect
        def _task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **kw):
            try:
                task_name = getattr(sender, 'name', str(sender))
                metrics.CELERY_TASK_COUNTER.labels(task_name=task_name, status='failure').inc()
            except Exception:
                logging.exception('Failed to record task_failure metrics')
    except Exception:
        # Celery not present or import failed; don't crash.
        logging.debug('Celery not available; skipping celery signal registration')


def setup():
    # Wrap cache get to count hits/misses
    _wrap_cache_get()
    # Register Celery signals for task duration
    _register_celery_signals()


# Run setup at import-time from AppConfig.ready()
setup()
