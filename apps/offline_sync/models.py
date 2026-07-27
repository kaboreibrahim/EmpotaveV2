import uuid

from django.conf import settings
from django.db import models


class SyncedAction(models.Model):
    """Trace chaque action hors ligne rejouee avec succes, indexee par la cle
    d'idempotence generee cote client (`client_action_id`). Le rejeu via
    Background Sync peut redelivrer la meme requete si la reponse du serveur
    n'est jamais arrivee jusqu'au client (ex. coupure juste apres l'ecriture
    en base) : dans ce cas la vue renvoie `result_snapshot` tel quel plutot
    que de reappliquer l'action une seconde fois.
    """
    client_action_id = models.UUIDField(unique=True, default=uuid.uuid4)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='synced_actions')
    endpoint = models.CharField(max_length=100)
    applied_at = models.DateTimeField(auto_now_add=True)
    result_snapshot = models.JSONField()

    class Meta:
        verbose_name = "Action synchronisee"
        verbose_name_plural = "Actions synchronisees"
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.endpoint} — {self.client_action_id}"
