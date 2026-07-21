"""
core/mixins.py
Mixin partagé entre toutes les apps.
TimestampMixin : clé primaire UUID + date_created automatique.
"""
import uuid
from django.db import models
from django.utils import timezone


class TimestampMixin(models.Model):
    """
    Fournit automatiquement :
      - id          : clé primaire UUID (non éditable)
      - date_created: date de création (non éditable)
    À utiliser en premier dans le MRO : class MonModel(TimestampMixin, SafeDeleteModel, LifecycleModel)
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date_created = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        abstract = True
