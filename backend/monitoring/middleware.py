import time
import logging
from django.utils.deprecation import MiddlewareMixin
from . import metrics


class PrometheusMiddleware(MiddlewareMixin):
    """Simple middleware that measures request latency and records to Prometheus."""

    def process_request(self, request):
        request._prom_start_time = time.time()

    def process_response(self, request, response):
        try:
            start = getattr(request, '_prom_start_time', None)
            if start is not None:
                duration = time.time() - start
                method = request.method
                path = metrics.safe_label_path(getattr(request, 'path', '/'))
                status_code = str(getattr(response, 'status_code', ''))
                metrics.REQUEST_LATENCY.labels(method=method, path=path, status_code=status_code).observe(duration)
        except Exception:
            logging.exception('Failed to record request latency')
        return response
