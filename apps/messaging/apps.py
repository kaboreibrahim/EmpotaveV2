from django.apps import AppConfig


class MessagingConfig(AppConfig):
    name = 'apps.messaging'
    verbose_name = 'Messagerie'

    def ready(self):
        from . import signals  # noqa: F401
