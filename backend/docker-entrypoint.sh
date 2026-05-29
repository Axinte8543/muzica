#!/usr/bin/env bash
set -e

# Wait for Redis to become available (uses python redis client installed in image)
if [ -n "$REDIS_URL" ]; then
  echo "Waiting for Redis at $REDIS_URL..."
  python - <<PY
import os, time
from urllib.parse import urlparse
url = os.environ.get('REDIS_URL')
if not url:
    raise SystemExit(0)
u = urlparse(url)
host = u.hostname or '127.0.0.1'
port = u.port or 6379
import redis
for i in range(60):
    try:
        r = redis.Redis(host=host, port=port, db=0)
        r.ping()
        print('Redis reachable')
        break
    except Exception as e:
        print('Redis not ready, retrying...', e)
        time.sleep(1)
else:
    print('Redis did not become ready, continuing anyway')
PY
fi

exec "$@"
