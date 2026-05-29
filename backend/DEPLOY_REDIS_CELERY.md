# Enabling Redis-backed cache and Celery (prod)

1. Copy `backend/.env.sample` to `backend/.env` and edit values (especially `SECRET_KEY` and DB settings if needed).

2. Start with Docker Compose (recommended for quick deploy/test):

```bash
docker compose up -d --build
```

This starts `redis`, `web`, `worker`, and `beat` services. All services use the same `REDIS_URL` defined in `backend/.env`.

3. If you deploy on a Linux server without Docker, use the provided `systemd` unit examples below (adjust paths and user):

Create `/etc/systemd/system/celery-worker.service`:

```ini
[Unit]
Description=Celery Worker for licenta
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/licenta-muzica/backend
EnvironmentFile=/path/to/licenta-muzica/backend/.env
ExecStart=/path/to/venv/bin/celery -A config worker --loglevel=info --concurrency=4
Restart=always

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/celery-beat.service`:

```ini
[Unit]
Description=Celery Beat for licenta
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/licenta-muzica/backend
EnvironmentFile=/path/to/licenta-muzica/backend/.env
ExecStart=/path/to/venv/bin/celery -A config beat --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

Then enable & start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now celery-worker
sudo systemctl enable --now celery-beat
sudo systemctl status celery-worker celery-beat
```

4. Post-deploy checks

- Verify Django app sees Redis cache: `python manage.py shell` -> `from django.core.cache import cache; cache.set('x', 1); cache.get('x')`
- Check Celery tasks: `celery -A config inspect active` (requires worker running)

5. Notes

- `LocMemCache` is per-process; enabling `USE_REDIS_CACHE=true` switches to `django-redis` backend (see `backend/config/settings.py`).
- Ensure `django-redis` and `redis` packages are installed in your Python env (they are listed in `backend/requirements.txt`). Add `celery` if missing.
