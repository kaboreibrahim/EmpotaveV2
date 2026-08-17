"""
apps/messaging/models.py
Messagerie interne : Conversation (dossier / privee / groupe), Message,
pieces jointes, accuses de lecture.

Un Group est une Conversation de type GROUPE dotee d'une identite propre
(nom, photo, description) : pas de modele GroupMember separe, l'appartenance
est portee par ConversationMember sur `Group.conversation` (cf. cahier des
charges : "eviter les duplications").
"""
import uuid

from django.conf import settings
from django.db import models
from django_lifecycle import LifecycleModel
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE

from core.mixins import TimestampMixin
from apps.common.fields import WebPImageField


# =============================================================================
# CONVERSATION
# =============================================================================

class Conversation(SafeDeleteModel, LifecycleModel, TimestampMixin):
    _safedelete_policy = SOFT_DELETE_CASCADE

    TYPE_DOSSIER = 'dossier'
    TYPE_PRIVEE  = 'privee'
    TYPE_GROUPE  = 'groupe'
    TYPE_CHOICES = [
        (TYPE_DOSSIER, 'Dossier'),
        (TYPE_PRIVEE,  'Privée'),
        (TYPE_GROUPE,  'Groupe'),
    ]

    type_conversation = models.CharField(max_length=10, choices=TYPE_CHOICES)
    # Rattachement metier optionnel : obligatoire (et unique) pour une
    # conversation de type DOSSIER, facultatif pour un groupe qui souhaite
    # aussi etre lie a un dossier. Jamais renseigne pour une conversation PRIVEE.
    dossier = models.ForeignKey(
        'conteneurs.Dossier', on_delete=models.CASCADE,
        related_name='conversations', null=True, blank=True,
    )
    titre         = models.CharField(max_length=255, blank=True, default='')
    date_modifier = models.DateTimeField(auto_now=True)

    membres = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through='ConversationMember',
        related_name='conversations',
    )

    class Meta:
        verbose_name        = "Conversation"
        verbose_name_plural = "Conversations"
        ordering            = ['-date_modifier']
        constraints = [
            # Une seule conversation "dossier" par dossier (un groupe peut
            # aussi referencer le meme dossier, cf. type_conversation != dossier).
            models.UniqueConstraint(
                fields=['dossier'],
                condition=models.Q(type_conversation='dossier'),
                name='une_seule_conversation_dossier_par_dossier',
            ),
        ]

    def __str__(self):
        if self.type_conversation == self.TYPE_DOSSIER and self.dossier_id:
            return f"Conversation dossier {self.dossier.TRD}"
        if self.titre:
            return self.titre
        return f"Conversation {self.get_type_conversation_display()} ({str(self.id)[:8]})"


class ConversationMember(models.Model):
    ROLE_MEMBRE = 'membre'
    ROLE_ADMIN  = 'admin'
    ROLE_CHOICES = [
        (ROLE_MEMBRE, 'Membre'),
        (ROLE_ADMIN,  'Administrateur'),
    ]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='membres_conversation')
    user         = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
    role         = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_MEMBRE)
    date_ajout   = models.DateTimeField(auto_now_add=True)

    # Pointeur leger pour le badge "non lus" (rapide, un seul champ a jour) ;
    # le detail par message (qui a lu quoi, utile pour les groupes) est dans
    # MessageRead. Pas de duplication : deux besoins differents.
    dernier_message_lu = models.ForeignKey(
        'Message', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    date_dernier_lu        = models.DateTimeField(null=True, blank=True)
    notifications_actives  = models.BooleanField(default=True)

    class Meta:
        verbose_name        = "Membre de conversation"
        verbose_name_plural = "Membres de conversation"
        constraints = [
            models.UniqueConstraint(fields=['conversation', 'user'], name='unique_membre_par_conversation'),
        ]
        indexes = [
            models.Index(fields=['user', 'conversation']),
        ]

    def __str__(self):
        return f"{self.user} dans {self.conversation}"


# =============================================================================
# MESSAGE
# =============================================================================

class Message(SafeDeleteModel, LifecycleModel, TimestampMixin):
    _safedelete_policy = SOFT_DELETE_CASCADE

    TYPE_TEXTE    = 'texte'
    TYPE_IMAGE    = 'image'
    TYPE_VIDEO    = 'video'
    TYPE_AUDIO    = 'audio'
    TYPE_DOCUMENT = 'document'
    TYPE_SYSTEME  = 'systeme'
    TYPE_CHOICES = [
        (TYPE_TEXTE,    'Texte'),
        (TYPE_IMAGE,    'Image'),
        (TYPE_VIDEO,    'Vidéo'),
        (TYPE_AUDIO,    'Audio / Vocal'),
        (TYPE_DOCUMENT, 'Document'),
        (TYPE_SYSTEME,  'Message système'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    auteur       = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='messages_envoyes',
    )
    type_message = models.CharField(max_length=10, choices=TYPE_CHOICES, default=TYPE_TEXTE)
    contenu      = models.TextField(blank=True, default='')
    reponse_a    = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='reponses',
    )
    est_supprime  = models.BooleanField(default=False)
    date_modifier = models.DateTimeField(auto_now=True)

    # Identifiant genere cote client (mode hors ligne, voir apps.offline_sync) :
    # sert de cle d'idempotence pour eviter les doublons si l'envoi est rejoue.
    client_message_id = models.UUIDField(null=True, blank=True, unique=True)

    class Meta:
        verbose_name        = "Message"
        verbose_name_plural = "Messages"
        ordering            = ['date_created']
        indexes = [
            models.Index(fields=['conversation', 'date_created']),
        ]

    def __str__(self):
        auteur = self.auteur or 'système'
        return f"Message de {auteur} dans {self.conversation} ({self.date_created:%Y-%m-%d %H:%M})"


class MessageAttachment(TimestampMixin):
    TYPE_IMAGE    = 'image'
    TYPE_VIDEO    = 'video'
    TYPE_AUDIO    = 'audio'
    TYPE_DOCUMENT = 'document'
    TYPE_CHOICES = [
        (TYPE_IMAGE,    'Image'),
        (TYPE_VIDEO,    'Vidéo'),
        (TYPE_AUDIO,    'Audio / Vocal'),
        (TYPE_DOCUMENT, 'Document'),
    ]

    message         = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='pieces_jointes')
    type_fichier    = models.CharField(max_length=10, choices=TYPE_CHOICES)
    fichier         = models.FileField(upload_to='messaging/attachments/%Y/%m/')
    miniature       = models.ImageField(upload_to='messaging/thumbnails/%Y/%m/', blank=True, null=True)
    nom_original    = models.CharField(max_length=255, blank=True, default='')
    taille_octets   = models.PositiveBigIntegerField(default=0)
    type_mime       = models.CharField(max_length=100, blank=True, default='')
    duree_secondes  = models.PositiveIntegerField(null=True, blank=True)  # audio / vidéo

    class Meta:
        verbose_name        = "Pièce jointe"
        verbose_name_plural = "Pièces jointes"
        ordering            = ['date_created']

    def __str__(self):
        return f"{self.nom_original or self.fichier.name} ({self.message_id})"


class MessageRead(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message       = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='lectures')
    user          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='messages_lus')
    date_lecture  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Lecture de message"
        verbose_name_plural = "Lectures de message"
        constraints = [
            models.UniqueConstraint(fields=['message', 'user'], name='unique_lecture_par_user'),
        ]
        indexes = [
            models.Index(fields=['message', 'user']),
        ]

    def __str__(self):
        return f"{self.user} a lu {self.message_id}"


# =============================================================================
# GROUPE
# =============================================================================

class Group(SafeDeleteModel, LifecycleModel, TimestampMixin):
    """Identite d'un groupe : sa Conversation (type GROUPE) porte les
    messages et les membres (via ConversationMember)."""
    _safedelete_policy = SOFT_DELETE_CASCADE

    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name='groupe')
    nom          = models.CharField(max_length=150)
    description  = models.TextField(blank=True, default='')
    photo        = WebPImageField(upload_to='messaging/groupes/', blank=True, null=True)
    cree_par     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='groupes_crees',
    )

    class Meta:
        verbose_name        = "Groupe"
        verbose_name_plural = "Groupes"
        ordering            = ['nom']

    def __str__(self):
        return self.nom
