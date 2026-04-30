from django.apps import AppConfig


class MarketplaceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketplace'
    verbose_name = '市场'

    def ready(self):
        import marketplace.signals  # noqa: F401 — enregistre les signaux
