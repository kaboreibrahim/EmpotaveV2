"""
apps/documents/models.py
Modèles : TypeDocument, Document
Aligné sur models.py v3 — architecture simplifiée :
  - Plus de modèles unitaires par type (FactureCommerciale, PackingList, etc.)
  - TypeDocument : référentiel (un enregistrement par type de doc)
  - Document     : modèle générique lié à Dossier + TypeDocument
  - TimestampMixin fournit id (UUID) + date_created
"""
from django.conf import settings
from django.db import models
from django_lifecycle import LifecycleModel
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE

from core.mixins import TimestampMixin
from apps.conteneurs.models import Dossier


# =============================================================================
# TYPE DOCUMENT (référentiel)
# =============================================================================

class TypeDocument(models.Model):
    """
    Référentiel des types de documents.
    À peupler via fixture ou admin :
      Facture Commerciale, Packing List, Certificat d'Origine,
      Confirmation Booking, Certificat Phytosanitaire, Copies BLS,
      Rapport Empotage, Rapport Sélection, Autorisation Exportation,
      EC, COA, Déclaration, IER Entrée, IER Sortie...
    """
    Id_TypeDocument = models.UUIDField(
        primary_key=True,
        default=__import__('uuid').uuid4,
        editable=False,
    )
    type_document = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name        = "Type de document"
        verbose_name_plural = "Types de documents"
        ordering            = ['type_document']

    def __str__(self):
        return self.type_document


# =============================================================================
# DOCUMENT GÉNÉRIQUE
# =============================================================================

class Document(SafeDeleteModel, LifecycleModel, TimestampMixin):
    """
    Document lié à un Dossier et un TypeDocument.
    Remplace les anciens modèles unitaires (FactureCommerciale, PackingList...).
    """
    _safedelete_policy = SOFT_DELETE_CASCADE

    STATUT_CHOICES = [
        ('ajoute',                 'Ajouté'),
        ('en_attente_validation',  'En attente de validation'),
        ('valide',                 'Validé'),
        ('rejete',                 'Rejeté'),
    ]

    dossier       = models.ForeignKey(Dossier,      on_delete=models.CASCADE, related_name='documents')
    type_document = models.ForeignKey(TypeDocument, on_delete=models.CASCADE, related_name='documents')
    fichier       = models.FileField(upload_to='documents/%Y/%m/%d/')
    date_modifier = models.DateTimeField(auto_now=True)
    statut        = models.CharField(max_length=25, choices=STATUT_CHOICES, default='ajoute')
    ajoute_par    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='documents_ajoutes',
    )

    class Meta:
        verbose_name        = "Document"
        verbose_name_plural = "Documents"
        ordering            = ['-date_created']

    def __str__(self):
        return f"{self.type_document} — {self.dossier.TRD} ({self.statut})"
