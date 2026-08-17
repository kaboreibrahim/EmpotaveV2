"""
apps/users/models.py
Modèles : Users (AbstractUser), CodeVerication, Personel
Aligné sur models.py v3 (TimestampMixin avec id UUID intégré).

Changements vs version précédente :
  - Personnel → Users (renommé pour suivre le MCD)
  - USER_TYPE_CHOICES simplifié : agent_selection, agent_empotage, personel, client
  - TimestampMixin fournit id (UUID) + date_created
  - Personel (sans 'n') = wrapper lié à Users (suit le MCD)
  - Signaux user_logged_in/out au niveau module (correction bug)
"""
import uuid

from django.contrib.auth.models import AbstractUser, Group
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from django_lifecycle import LifecycleModel
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE
from safedelete.signals import post_softdelete

from core.mixins import TimestampMixin
from apps.common.fields import WebPImageField


# =============================================================================
# UTILISATEURS
# =============================================================================

class Users(AbstractUser, SafeDeleteModel):
    """
    Modèle utilisateur central.
    NB : AUTH_USER_MODEL = 'users.Users'
    TimestampMixin non utilisé ici car AbstractUser a déjà son propre PK.
    """
    _safedelete_policy = SOFT_DELETE_CASCADE

    USER_TYPE_CHOICES = [
        ('agent_selection', 'Agent de Sélection'),
        ('agent_empotage',  'Agent Habillage & Empotage'),
        ('personnel',        'Personnel'),
        ('client',          'Client'),
        ('comptable',       'Comptable'),
    ]

    numero       = models.CharField(max_length=20, blank=True, null=True)
    photo        = WebPImageField(upload_to='users/photos/', blank=True, null=True)
    date_created = models.DateTimeField(default=timezone.now, editable=False)
    is_verified  = models.BooleanField(default=False)
    user_type    = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    pays         = models.ForeignKey(
        'referentiels.Pays',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
    )
    entreprise   = models.ForeignKey(
        'companies.Company',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
    )
    is_online    = models.BooleanField(default=False)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='users_otl_set',
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='users_otl_permissions_set',
        blank=True,
    )

    class Meta:
        verbose_name        = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        return self.username


@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    if hasattr(user, 'is_online'):
        user.is_online  = True
        user.last_login = timezone.now()
        user.save(update_fields=['is_online', 'last_login'])


@receiver(user_logged_out)
def user_logged_out_handler(sender, request, user, **kwargs):
    if user and hasattr(user, 'is_online'):
        user.is_online = False
        user.save(update_fields=['is_online'])


# =============================================================================
# CODE VERIFICATION
# =============================================================================

class CodeVerication(models.Model):
    """Code OTP pour reset/forgot/validate."""
    Id_Verication = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user          = models.OneToOneField(Users, on_delete=models.CASCADE)
    code          = models.CharField(max_length=6)
    date_created  = models.DateTimeField(auto_now_add=True)
    typecode      = models.CharField(
        max_length=10,
        choices=[
            ('rest',     'Reset'),
            ('forgat',   'Forgot'),
            ('validate', 'Validate'),
        ],
    )

    class Meta:
        verbose_name = "Code de vérification"

    def __str__(self):
        return f"{self.user.username} — {self.typecode}"


# =============================================================================
# PERSONNEL INTERNE
# =============================================================================

class Personnel(SafeDeleteModel, LifecycleModel, TimestampMixin):
    """
    Personnel interne — wrapper lié à Users.
    TimestampMixin fournit id (UUID) + date_created.
    """
    _safedelete_policy = SOFT_DELETE_CASCADE
    # id hérité de TimestampMixin (UUID)
    user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name='personel')

    class Meta:
        verbose_name        = "Personnel interne"
        verbose_name_plural = "Personnel interne"

    def __str__(self):
        return str(self.user)


# =============================================================================
# CLIENT
# =============================================================================

class Client(SafeDeleteModel, LifecycleModel, TimestampMixin):
    _safedelete_policy = SOFT_DELETE_CASCADE

    user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name='client')

    
    class Meta:
        verbose_name        = "Client"
        verbose_name_plural = "Clients"
        
    def __str__(self):
        return str(self.user)



# =============================================================================
# AGENTS   
# =============================================================================

class Agent_selection(SafeDeleteModel, LifecycleModel, TimestampMixin):
    _safedelete_policy = SOFT_DELETE_CASCADE
    
    user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name='agent_selection')


    class Meta:
        verbose_name        = "Agent de sélection"
        verbose_name_plural = "Agents de sélection "

    def __str__(self):
        return str(self.user)


class Agent_empotage(SafeDeleteModel, LifecycleModel, TimestampMixin):
    _safedelete_policy = SOFT_DELETE_CASCADE
    user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name='agent_empotage')

    class Meta:
        verbose_name        = "Agent d'empotage "
        verbose_name_plural = "Agents d'empotage "

    def __str__(self):
        return str(self.user)


# =============================================================================
# PERSONNEL COMPTABLE
# =============================================================================

class PersonnelComptable(SafeDeleteModel, LifecycleModel, TimestampMixin):
    """Wrapper lié à Users pour le rôle Comptable (accès à comptabiliteDashboard,
    validation des paiements)."""
    _safedelete_policy = SOFT_DELETE_CASCADE
    user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name='personnel_comptable')

    class Meta:
        verbose_name        = "Personnel comptable"
        verbose_name_plural = "Personnel comptable"

    def __str__(self):
        return str(self.user)


@receiver(post_save, sender=PersonnelComptable)
def personnel_comptable_created_handler(sender, instance, created, **kwargs):
    """Ajoute automatiquement l'utilisateur au groupe Django "Comptable"
    (droits d'accès à comptabiliteDashboard + validation des paiements)."""
    if created:
        groupe, _ = Group.objects.get_or_create(name='Comptable')
        instance.user.groups.add(groupe)


@receiver([post_delete, post_softdelete], sender=PersonnelComptable)
def personnel_comptable_deleted_handler(sender, instance, **kwargs):
    """Retire l'utilisateur du groupe "Comptable" que la suppression soit
    un soft-delete (cas normal) ou un delete définitif."""
    groupe = Group.objects.filter(name='Comptable').first()
    if groupe:
        instance.user.groups.remove(groupe)


 