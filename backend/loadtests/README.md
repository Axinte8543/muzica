# Load testing

This folder contains a Locust benchmark for the authenticated API flow used in the thesis.

## What it measures

The scenario reuses seeded credentials and exercises the most important read paths:

- `GET /api/home/`
- `GET /api/recommendations/`
- `GET /api/chat/conversations/`
- `GET /api/chat/messages/?conversation=:id`
- `GET /api/users/search/?q=:query`

Locust reports response-time percentiles, request rates, and failures. The thesis can cite p95 and p99 latency from a headless run.

## How to run

1. Install dependencies.
2. Seed the deterministic E2E dataset.
3. Start Django on `127.0.0.1:8000`.
4. Run Locust in headless mode.

Example:

```bash
python manage.py seed_e2e_flow --reset
python manage.py runserver 127.0.0.1:8000
locust -f loadtests/locustfile.py --headless -u 10 -r 2 -t 1m --host http://127.0.0.1:8000
```

## CI baseline

The repository includes a GitHub Actions workflow at [`.github/workflows/backend-loadtest.yml`](../../.github/workflows/backend-loadtest.yml) that:

- seeds the deterministic E2E dataset
- starts Django on `127.0.0.1:8000`
- waits for the `/health/` endpoint
- runs a headless Locust baseline with CSV artifact output

The workflow uploads `backend/loadtests/results/` and the server log as artifacts so p95/p99 results can be reviewed after each run.

Environment variables:

- `LOADTEST_HOST` for a custom base URL
- `LOADTEST_USERNAME` for the test account username
- `LOADTEST_PASSWORD` for the test account password
