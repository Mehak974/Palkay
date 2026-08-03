from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'catalog'

    def ready(self):
        # Connect cache invalidation signals
        try:
            from palkay.cache import _connect_signals
            _connect_signals()
        except Exception:
            pass
