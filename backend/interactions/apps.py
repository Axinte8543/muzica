from django.apps import AppConfig


class InteractionsConfig(AppConfig):
    name = 'interactions'
    
    def ready(self):
        """Register signal handlers when app is ready."""
        import interactions.signals  # noqa
