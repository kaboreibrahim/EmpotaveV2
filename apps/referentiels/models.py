"""
apps/referentiels/models.py
Modèles : Pays, Commodite, POL, POD, CompagnieMaritime,
          SiteSelection, SiteEmpotage, Agent_selection, Agent_empotage, Client

Aligné sur models.py v3 :
  - TimestampMixin fournit id (UUID) + date_created sur tous les modèles
  - Commodite : champs icon + sig ajoutés
  - SiteSelection / SiteEmpotage remplacent Site / Site_empotage (nouveaux noms MCD)
  - Agent_selection + Agent_empotage : deux modèles distincts (remplace Agent unique)
  - Client déplacé ici car référentiel pur (pas de logique dossier)
"""
from django.db import models
from django_lifecycle import LifecycleModel
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE

from core.mixins import TimestampMixin
from apps.common.fields import WebPImageField


# =============================================================================
# PAYS
# =============================================================================

class Pays(SafeDeleteModel, LifecycleModel, TimestampMixin):
    _safedelete_policy = SOFT_DELETE_CASCADE
    nom     = models.CharField(max_length=100, unique=True)
    drapeau = WebPImageField(upload_to='pays/drapeaux/', blank=True, null=True)

    class Meta:
        verbose_name        = "Pays"
        verbose_name_plural = "Pays"
        ordering            = ['nom']

    def __str__(self):
        return self.nom


# =============================================================================
# COMMODITE
# =============================================================================

class Commodite(SafeDeleteModel, LifecycleModel, TimestampMixin):
    _safedelete_policy = SOFT_DELETE_CASCADE
    nom     = models.CharField(max_length=100)
    icon    = WebPImageField(upload_to='commodites/icons/', blank=True, null=True)
    sig     = models.CharField(max_length=20, blank=True, null=True, verbose_name="Sigle")
    Id_Pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='commodites')

    class Meta:
        verbose_name        = "Commodité"
        verbose_name_plural = "Commodités"
        ordering            = ['nom']

    def __str__(self):
        return self.nom


# =============================================================================
# PORTS
# =============================================================================

class POL(SafeDeleteModel, LifecycleModel, TimestampMixin):
    """Port of Loading"""
    _safedelete_policy = SOFT_DELETE_CASCADE
    nom     = models.CharField(max_length=100)
    lieu    = models.CharField(max_length=200)
    Id_Pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='pols')

    class Meta:
        verbose_name        = "Port de chargement (POL)"
        verbose_name_plural = "Ports de chargement (POL)"

    def __str__(self):
        return self.nom


class POD(SafeDeleteModel, LifecycleModel, TimestampMixin):
    """Port of Discharge"""
    _safedelete_policy = SOFT_DELETE_CASCADE
    nom     = models.CharField(max_length=100)
    lieu    = models.CharField(max_length=200)
    Id_Pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='pods')

    class Meta:
        verbose_name        = "Port de déchargement (POD)"
        verbose_name_plural = "Ports de déchargement (POD)"

    def __str__(self):
        return self.nom


# =============================================================================
# COMPAGNIE MARITIME
# =============================================================================

class CompagnieMaritime(SafeDeleteModel, LifecycleModel, TimestampMixin):
    _safedelete_policy = SOFT_DELETE_CASCADE
    nom     = models.CharField(max_length=100)
    lieu    = models.CharField(max_length=200)
    Id_Pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='compagnies_maritimes')

    class Meta:
        verbose_name        = "Compagnie maritime"
        verbose_name_plural = "Compagnies maritimes"

    def __str__(self):
        return self.nom


# =============================================================================
# SITES
# =============================================================================

class SiteSelection(SafeDeleteModel, LifecycleModel, TimestampMixin):
    _safedelete_policy = SOFT_DELETE_CASCADE
    nom     = models.CharField(max_length=100)
    contact = models.CharField(max_length=50)
    lieu    = models.CharField(max_length=200)
    Id_Pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='sites_selection')

    class Meta:
        verbose_name        = "Site de sélection"
        verbose_name_plural = "Sites de sélection"

    def __str__(self):
        return self.nom


class SiteEmpotage(SafeDeleteModel, LifecycleModel, TimestampMixin):
    _safedelete_policy = SOFT_DELETE_CASCADE
    nom     = models.CharField(max_length=100)
    contact = models.CharField(max_length=50)
    lieu    = models.CharField(max_length=200)
    Id_Pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='sites_empotage')

    class Meta:
        verbose_name        = "Site d'empotage"
        verbose_name_plural = "Sites d'empotage"

    def __str__(self):
        return self.nom

