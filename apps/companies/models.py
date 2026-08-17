"""
apps/companies/models.py
Modele Company : les societes du groupe (Oils of Africa, Africa Newport
Logistics, OTL & Bulk Liquid). Chaque utilisateur appartient a une entreprise
(voir Users.entreprise dans apps.users.models).
"""
from django.db import models
from django_lifecycle import LifecycleModel
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE

from core.mixins import TimestampMixin
from apps.common.fields import WebPImageField


class Company(SafeDeleteModel, LifecycleModel, TimestampMixin):
    _safedelete_policy = SOFT_DELETE_CASCADE

    nom     = models.CharField(max_length=100, unique=True)
    slug    = models.SlugField(max_length=100, unique=True)
    logo    = WebPImageField(upload_to='companies/logos/', blank=True, null=True)
    couleur = models.CharField(
        max_length=7, default='#00450d',
        help_text="Couleur d'accent (hex), ex : #00450d",
    )
    actif   = models.BooleanField(default=True)

    class Meta:
        verbose_name        = "Entreprise"
        verbose_name_plural = "Entreprises"
        ordering            = ['nom']

    def __str__(self):
        return self.nom
