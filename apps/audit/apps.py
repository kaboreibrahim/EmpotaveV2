from django.apps import AppConfig
from django.db.models.signals import post_delete, post_save, pre_save


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit'
    verbose_name = "Audit"

    def ready(self):
        from . import signals

        pre_save.connect(signals.pre_save_snapshot, dispatch_uid='audit_pre_save_snapshot')
        post_save.connect(signals.log_save, dispatch_uid='audit_post_save')
        post_delete.connect(signals.log_delete, dispatch_uid='audit_post_delete')
