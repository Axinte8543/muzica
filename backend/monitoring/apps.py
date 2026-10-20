from django.apps import AppConfig
import logging


class MonitoringConfig(AppConfig):
    name = 'monitoring'

    def ready(self):
                                                                               
        try:
                                                                               
            from . import metrics              
            from . import hooks                
        except Exception:
            logging.exception('Failed to initialize monitoring metrics/signals')
