from django.http import JsonResponse, HttpResponse
from django.db import connections
import logging

try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
except Exception:
    generate_latest = None
    CONTENT_TYPE_LATEST = 'text/plain; version=0.0.4; charset=utf-8'

try:
    import sentry_sdk
except Exception:
    sentry_sdk = None


def health(request):
    """Simple health endpoint that verifies DB connectivity."""
    try:
        with connections['default'].cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception as exc:
        logging.exception('Health check failed')
        if sentry_sdk:
            try:
                sentry_sdk.capture_exception(exc)
            except Exception:
                pass
        return JsonResponse({'status': 'error', 'detail': str(exc)}, status=500)

    return JsonResponse({'status': 'ok'})


def metrics(request):
    """Expose Prometheus metrics if prometheus_client is available."""
    if not generate_latest:
        return HttpResponse('prometheus_client not installed', status=501)
    try:
        output = generate_latest()
        return HttpResponse(output, content_type=CONTENT_TYPE_LATEST)
    except Exception:
        logging.exception('Failed to render metrics')
        return HttpResponse(status=500)
