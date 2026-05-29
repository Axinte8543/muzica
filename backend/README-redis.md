Production cache with Redis

This project uses Django's cache API. By default (development/tests) the
project uses an in-memory `LocMemCache` backend. For production you should
use a persistent Redis cache and the `django-redis` backend.

Quick setup:

- Install packages in your production environment:

```bash
pip install -r backend/requirements.txt
```

- Set environment variables (example):

```bash
export REDIS_URL=redis://redis-host:6379/1
export USE_REDIS_CACHE=true
```

- Ensure `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` also point to Redis.
- Restart the Django app and the Celery worker/beat so they pick up the new cache.

Why this matters:

- `LocMemCache` is per-process and not shared across web/Celery workers.
- Recommender and compatibility caches rely on a shared cache (Redis) to
  avoid expensive on-request recomputations.

Recommended settings snippet (already supported by `config/settings.py`):

```py
# in backend/config/settings.py
REDIS_URL = config('REDIS_URL')
USE_REDIS_CACHE = config('USE_REDIS_CACHE', default=True, cast=bool)
# CACHES will use django-redis when enabled
```

Operational notes:

- `IGNORE_EXCEPTIONS=True` is enabled so cache failures don't crash requests.
  Monitor Redis availability and set alerts instead of relying on this flag.
- After enabling Redis, run the precompute tasks (or wait for scheduled jobs):

```bash
python manage.py precompute_recommendations --limit 12
python manage.py precompute_compatibility --limit 50
```
