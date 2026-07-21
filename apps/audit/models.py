"""
apps/audit/models.py
Journal d'audit générique : une entrée par création/modification/suppression
détectée automatiquement (voir signals.py) sur n'importe quel modèle des apps
du projet (apps.*), via ContentType + GenericForeignKey.
"""
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class AuditLog(models.Model):
    ACTION_CREATE = 'create'
    ACTION_UPDATE = 'update'
    ACTION_DELETE = 'delete'
    ACTION_DOWNLOAD = 'download'
    ACTION_SUBMIT = 'submit'
    ACTION_CHOICES = [
        (ACTION_CREATE, 'Création'),
        (ACTION_UPDATE, 'Modification'),
        (ACTION_DELETE, 'Suppression'),
        (ACTION_DOWNLOAD, 'Téléchargement'),
        (ACTION_SUBMIT, 'Soumission'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64)
    content_object = GenericForeignKey('content_type', 'object_id')
    object_repr = models.CharField(max_length=255)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    actor_username = models.CharField(max_length=150, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    changes = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Journal d'audit"
        verbose_name_plural = "Journal d'audit"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} — {self.object_repr} ({self.actor_username or 'système'})"
