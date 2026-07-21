"""
apps/notifications/models.py
Modèle : Notification
Aligné sur models.py v3 — TimestampMixin, FK vers Users.
"""
from django.db import models
from django_lifecycle import LifecycleModel
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE

from core.mixins import TimestampMixin
from apps.users.models import Users


class Notification(SafeDeleteModel, LifecycleModel, TimestampMixin):
    _safedelete_policy = SOFT_DELETE_CASCADE

    CATEGORIE_INFO = 'info'
    CATEGORIE_ALERTE = 'alerte'
    CATEGORIE_CHOICES = [
        (CATEGORIE_INFO, 'Information'),
        (CATEGORIE_ALERTE, 'Alerte'),
    ]

    user      = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='notifications')
    message   = models.TextField()
    is_read   = models.BooleanField(default=False)
    categorie = models.CharField(max_length=10, choices=CATEGORIE_CHOICES, default=CATEGORIE_INFO)

    class Meta:
        verbose_name        = "Notification"
        verbose_name_plural = "Notifications"
        ordering            = ['-date_created']

    def __str__(self):
        return f"Notif {self.user.username} — {self.message[:40]}..."
