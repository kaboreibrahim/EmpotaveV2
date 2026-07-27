from django.apps import AppConfig


class OfflineSyncConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.offline_sync'
    verbose_name = "Synchronisation hors ligne"
