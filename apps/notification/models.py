"""
apps/notification/models.py
Modèles : Notification (in-app) et PushSubscription (Web Push / VAPID).
Alignés sur models.py v3 — TimestampMixin, FK vers Users.
"""
import uuid

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

    TYPE_DOSSIER_CREE = 'dossier_cree'
    TYPE_PAIEMENT_VALIDE = 'paiement_valide'
    TYPE_CHANGEMENT_STATUT = 'changement_statut'
    TYPE_DOCUMENT_AJOUTE = 'document_ajoute'
    TYPE_RETOUR_SELECTION = 'retour_selection'
    TYPE_RETOUR_EMPOTAGE = 'retour_empotage'
    TYPE_NOUVEAU_MESSAGE = 'nouveau_message'
    TYPE_AJOUT_GROUPE = 'ajout_groupe'
    TYPE_AJOUT_CONVERSATION = 'ajout_conversation'
    TYPE_AUTRE = 'autre'
    TYPE_NOTIFICATION_CHOICES = [
        (TYPE_DOSSIER_CREE, 'Dossier créé'),
        (TYPE_PAIEMENT_VALIDE, 'Paiement validé'),
        (TYPE_CHANGEMENT_STATUT, 'Changement de statut'),
        (TYPE_DOCUMENT_AJOUTE, 'Document ajouté'),
        (TYPE_RETOUR_SELECTION, 'Retour en sélection'),
        (TYPE_RETOUR_EMPOTAGE, 'Retour en empotage'),
        (TYPE_NOUVEAU_MESSAGE, 'Nouveau message'),
        (TYPE_AJOUT_GROUPE, 'Ajout à un groupe'),
        (TYPE_AJOUT_CONVERSATION, 'Ajout à une conversation'),
        (TYPE_AUTRE, 'Autre'),
    ]

    user      = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='notifications')
    dossier   = models.ForeignKey(
        'conteneurs.Dossier', on_delete=models.CASCADE, related_name='notifications',
        null=True, blank=True,
    )
    conversation = models.ForeignKey(
        'messaging.Conversation', on_delete=models.CASCADE, related_name='notifications',
        null=True, blank=True,
    )
    titre     = models.CharField(max_length=255, blank=True, default='')
    message   = models.TextField()
    type_notification = models.CharField(
        max_length=20, choices=TYPE_NOTIFICATION_CHOICES, default=TYPE_AUTRE,
    )
    url       = models.CharField(max_length=500, blank=True, default='')
    is_read   = models.BooleanField(default=False)
    categorie = models.CharField(max_length=10, choices=CATEGORIE_CHOICES, default=CATEGORIE_INFO)

    class Meta:
        verbose_name        = "Notification"
        verbose_name_plural = "Notifications"
        ordering            = ['-date_created']

    def __str__(self):
        return f"Notif {self.user.username} — {self.message[:40]}..."

    @property
    def lu(self):
        """Alias lisible du champ `is_read` (nom demandé par le cahier des charges)."""
        return self.is_read


class PushSubscription(models.Model):
    """Abonnement Web Push d'un navigateur/appareil pour un utilisateur donné.

    Un même utilisateur peut avoir plusieurs abonnements (plusieurs navigateurs
    ou appareils) ; un même endpoint ne peut appartenir qu'à un seul abonnement
    (ré-abonnement depuis le même navigateur = mise à jour, pas de doublon).
    """
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur  = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint     = models.URLField(max_length=500, unique=True)
    p256dh       = models.CharField(max_length=255)
    auth         = models.CharField(max_length=255)
    user_agent   = models.CharField(max_length=255, blank=True, default='')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Abonnement Push"
        verbose_name_plural = "Abonnements Push"
        ordering            = ['-created_at']

    def __str__(self):
        return f"Push {self.utilisateur.username} — {self.endpoint[:60]}..."
