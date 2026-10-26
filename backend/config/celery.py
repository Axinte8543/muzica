import functools
import os

try:
    from celery import Celery
except Exception:
    Celery = None


class _LocalTask:
    def __init__(self, func, *, bind=False):
        functools.update_wrapper(self, func)
        self._func = func
        self._bind = bind

    def __call__(self, *args, **kwargs):
        if self._bind:
            return self._func(None, *args, **kwargs)
        return self._func(*args, **kwargs)

    def run(self, *args, **kwargs):
        return self.__call__(*args, **kwargs)

    def delay(self, *args, **kwargs):
        return self.__call__(*args, **kwargs)

    def apply_async(self, args=None, kwargs=None, countdown=None, **options):
        return self.__call__(*(args or ()), **(kwargs or {}))


class _LocalCeleryApp:
    def task(self, *decorator_args, **decorator_kwargs):
        def decorator(func):
            return _LocalTask(func, bind=bool(decorator_kwargs.get('bind', False)))

        if decorator_args and callable(decorator_args[0]) and len(decorator_args) == 1 and not decorator_kwargs:
            return decorator(decorator_args[0])
        return decorator

    def config_from_object(self, *args, **kwargs):
        return None

    def autodiscover_tasks(self, *args, **kwargs):
        return None

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

if Celery is not None:
    app = Celery('config')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    app.autodiscover_tasks()
else:
    app = _LocalCeleryApp()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
