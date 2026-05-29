from django.apps import AppConfig
import logging


class MonitoringConfig(AppConfig):
    name = 'monitoring'

    def ready(self):
        # Import side-effect modules that register metrics and signal handlers.
        try:
            # Import here to avoid import-time side effects during Django setup
            from . import metrics  # noqa: F401
            from . import hooks    # noqa: F401
        except Exception:
            logging.exception('Failed to initialize monitoring metrics/signals')
