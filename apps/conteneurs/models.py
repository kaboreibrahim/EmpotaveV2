"""
apps/conteneurs/models.py
Modèles : Dossier, ConteneurCommunMixin, ISOTanks, Flexitanks

Aligné sur models.py v3 :
  - TimestampMixin fournit id (UUID) + date_created
  - Dossier : statuts simplifiés (en_attente, selection_en_cours,
    empotage_en_cours, dossier_termine, annulé)
  - FKs Dossier → nouveaux noms (Id_Pays, Id_POD, Id_POL, Id_SiteSelection,
    Id_SiteEmpotage, Id_Commodite, Id_CompagnieMaritime, id_client,
    Id_Agent_selection, Id_Agent_empotage, Id_Personnel)
  - ConteneurCommunMixin : mixin abstrait, hérité directement par
    ISOTanks et Flexitanks (un conteneur est nécessairement l'un des deux,
    jamais une entité "de base" indépendante)
"""
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import FileExtensionValidator
from django.db import models

from apps.common.fields import WebPImageField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_lifecycle import LifecycleModel
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE

from core.mixins import TimestampMixin
from apps.referentiels.models import (
    Pays, Commodite, POL, POD, CompagnieMaritime,
    SiteSelection, SiteEmpotage,
    
)
from apps.users.models import (Personnel, Agent_selection, 
    Agent_empotage, Client,

)


# =============================================================================
# DOSSIER
# =============================================================================

class Dossier(SafeDeleteModel, LifecycleModel, TimestampMixin):
    _safedelete_policy = SOFT_DELETE_CASCADE

    STATUT_CHOICES = [
        ('en_attente',         _('En Attente')),
        ('selection_en_cours', _('Sélection en cours')),
        ('empotage_en_cours',  _('Empotage en cours')),
        ('dossier_termine',    _('Terminé')),
        ('annulé',             _('Annulé')),
    ]

    TAILLE_CONTENEUR = [
        ('10_pieds',     _('10 Pieds')),
        ('20_pieds',     _('20 Pieds')),
        ('ISO_20_pieds', _('ISO Tank 20 Pieds')),
        ('40_pieds',     _('40 Pieds')),
    ]

    statut         = models.CharField(max_length=25, choices=STATUT_CHOICES, default='en_attente')
    TRD            = models.CharField(max_length=50, verbose_name="Numéro TRD")
    projet         = models.CharField(max_length=100)
    Booking        = models.CharField(max_length=100)
    type_conteneur = models.CharField(max_length=13, choices=TAILLE_CONTENEUR)

    # Dates de suivi (toutes nullable)
    date_de_selection              = models.DateTimeField(null=True, blank=True) # saisir par l'agent de sélection
    date_de_empotage               = models.DateTimeField(null=True, blank=True) # saisir par l'agent d'empotage
    date_de_soumission_du_rapport  = models.DateTimeField(null=True, blank=True) # saisir automatiquement quand le rapport est soumis

    commentaire_creation   = models.TextField(blank=True, verbose_name="Commentaire de création") # saisi par le personnel lors de la création du dossier
    commentaire_soumission = models.TextField(blank=True, verbose_name="Commentaire de soumission") # saisi par l'agent de sélection lors de la soumission du dossier

    # Référentiels
    Id_Pays              = models.ForeignKey(Pays,              on_delete=models.CASCADE,  related_name='dossiers')
    Id_POD               = models.ForeignKey(POD,               on_delete=models.CASCADE,  related_name='dossiers')
    Id_POL               = models.ForeignKey(POL,               on_delete=models.CASCADE,  related_name='dossiers')
    Id_Commodite         = models.ForeignKey(Commodite,         on_delete=models.CASCADE,  related_name='dossiers')
    Id_CompagnieMaritime = models.ForeignKey(CompagnieMaritime, on_delete=models.CASCADE,  related_name='dossiers')
    Id_SiteSelection     = models.ForeignKey(SiteSelection,     on_delete=models.CASCADE,  related_name='dossiers')
    Id_SiteEmpotage      = models.ForeignKey(SiteEmpotage,      on_delete=models.CASCADE,  related_name='dossiers')

    # Acteurs (optionnels selon MCD)
    Id_Agent_selection = models.ForeignKey(Agent_selection, on_delete=models.SET_NULL, null=True, blank=True, related_name='dossiers')
    Id_Agent_empotage  = models.ForeignKey(Agent_empotage,  on_delete=models.SET_NULL, null=True, blank=True, related_name='dossiers')
    id_client          = models.ForeignKey(Client,          on_delete=models.CASCADE,                         related_name='dossiers')
    Id_Personnel        = models.ForeignKey(Personnel,        on_delete=models.SET_NULL, null=True, blank=True, related_name='dossiers_crees')
    Id_Agent_operationel=models.ForeignKey(Personnel, on_delete=models.SET_NULL, null=True, blank=True, related_name='dossiers_operationnel')

    # Paiement (verrou avant traitement par les agents)
    est_paye             = models.BooleanField(default=False)
    date_paiement        = models.DateTimeField(null=True, blank=True)
    commentaire_paiement = models.TextField(blank=True)
    montant_paiement     = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    preuve_paiement      = models.FileField(
        upload_to='paiements/preuves/%Y/%m/', null=True, blank=True,
        validators=[FileExtensionValidator(['pdf'])],
    )
    utilisateur_paiement = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='paiements_valides',
    )

    class Meta:
        verbose_name        = "Dossier"
        verbose_name_plural = "Dossiers"
        ordering            = ['-date_created']
        permissions          = [
            ('can_valider_paiement', "Peut valider le paiement d'un dossier"),
            ('can_voir_paiements', "Peut voir le suivi des paiements des dossiers"),
        ]

    def __str__(self):
        pays_nom = self.Id_Pays.nom if self.Id_Pays_id else ''
        return f"Dossier {self.TRD} — {self.projet} ({pays_nom})"

    @property
    def nature_conteneurs(self):
        has_iso = self.isotanks.exists()
        has_flexitank = self.flexitanks.exists()
        if has_iso and has_flexitank:
            return "mixte"
        if has_iso:
            return "iso"
        if has_flexitank:
            return "flexitank"
        return "aucun"

    # ------------------------------------------------------------------
    # Transitions de statut
    # ------------------------------------------------------------------

    def demarrer_selection(self):
        if self.statut == 'en_attente':
            self.statut            = 'selection_en_cours'
            self.date_de_selection = timezone.now()
            self.save()

    def demarrer_empotage(self):
        if self.statut == 'selection_en_cours':
            self.statut          = 'empotage_en_cours'
            self.date_de_empotage = timezone.now()
            self.save()

    def soumettre_rapport(self, commentaire=''):
        self.date_de_soumission_du_rapport = timezone.now()
        update_fields = ['date_de_soumission_du_rapport']
        if commentaire:
            self.commentaire_soumission = commentaire
            update_fields.append('commentaire_soumission')
        self.save(update_fields=update_fields)

    def terminer(self):
        self.statut                 = 'dossier_termine'
        self.date_de_fin_d_empotage = timezone.now()
        self.save()

    def annuler(self):
        self.statut = 'annulé'
        self.save(update_fields=['statut'])

    def valider_paiement(self, user, commentaire='', date_paiement=None, montant=None, preuve=None):
        """Enregistre le paiement du dossier et le débloque pour les agents."""
        self.est_paye = True
        self.date_paiement = date_paiement or timezone.now()
        self.commentaire_paiement = commentaire
        self.utilisateur_paiement = user
        update_fields = ['est_paye', 'date_paiement', 'commentaire_paiement', 'utilisateur_paiement']
        if montant is not None:
            self.montant_paiement = montant
            update_fields.append('montant_paiement')
        if preuve is not None:
            self.preuve_paiement = preuve
            update_fields.append('preuve_paiement')
        self.save(update_fields=update_fields)

    def retrograder_apres_terminaison(self):
        """Rouvre un dossier termine : le repasse en empotage_en_cours pour correction
        par l'agent d'empotage (voir la notification envoyee par la vue appelante)."""
        if self.statut == 'dossier_termine':
            self.statut = 'empotage_en_cours'
            self.save(update_fields=['statut'])

    def retourner_en_selection(self):
        """Remet le dossier en sélection + notifie tout le personnel."""
        if self.statut == 'empotage_en_cours':
            self.statut            = 'selection_en_cours'
            self.date_de_selection = timezone.now()
            self.save()
            emails_personnel = list(
                Personnel.objects
                .filter(user__is_active=True)
                .exclude(user__email='')
                .values_list('user__email', flat=True)
            )
            if emails_personnel:
                send_mail(
                    subject=f"Dossier à mettre à jour : {self.projet}",
                    message=(
                        f"Bonjour,\n\n"
                        f"Le dossier {self.TRD} — {self.projet} "
                        "vous a été retourné pour mise à jour.\n"
                        "Merci de votre attention."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=emails_personnel,
                    fail_silently=False,
                )


# =============================================================================
# CONTENEUR COMMUN (mixin abstrait)
# =============================================================================

class ConteneurCommunMixin(SafeDeleteModel, LifecycleModel, TimestampMixin):
    """
    Champs et logique communs à tout conteneur (ISO Tank ou Flexitank).
    Mixin abstrait : ne crée aucune table, hérité directement par ISOTanks
    et Flexitanks. Un conteneur est toujours l'un des deux, jamais une
    entité "de base" indépendante.
    """
    _safedelete_policy = SOFT_DELETE_CASCADE

    ETAT_CHOICES = [
        ('excellent', _('Excellent')),
        ('moyen',     _('Moyen')),
        ('mauvais',   _('Mauvais')),
    ]

    STATUT_CHOICES = [
        ('non_empote', _('Non empoté')),
        ('empote',     _('Empoté')),
    ]

    dossier   = models.ForeignKey(Dossier, on_delete=models.CASCADE, related_name='%(class)s')
    statut    = models.CharField(max_length=20, choices=STATUT_CHOICES, default='non_empote')
    reference = models.CharField(max_length=50, unique=True)
    etat      = models.CharField(max_length=10, choices=ETAT_CHOICES)

    # Photos (communes)
    #image de empotage
    photo_debut          = WebPImageField(upload_to='conteneurs/debut/',          blank=True, null=True)
    photo_pendant        = WebPImageField(upload_to='conteneurs/pendant/',        blank=True, null=True)
    photo_fin            = WebPImageField(upload_to='conteneurs/fin/',            blank=True, null=True)

    #image de selection
    photo_devant         = WebPImageField(upload_to='conteneurs/devant/',         blank=True, null=True)
    photo_derriere       = WebPImageField(upload_to='conteneurs/derriere/',       blank=True, null=True)
    photo_interieur      = WebPImageField(upload_to='conteneurs/interieur/',      blank=True, null=True)
    photo_lateral_droit  = WebPImageField(upload_to='conteneurs/lateral_droit/',  blank=True, null=True)
    photo_lateral_gauche = WebPImageField(upload_to='conteneurs/lateral_gauche/', blank=True, null=True)

    # Température
    Temerature = models.FloatField("Température (°C)", null=True, blank=True)

    # Poids
    poids_net         = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), blank=True, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.reference} ({self.get_statut_display()})"

    def verifier_statut(self):
        requis = [self.poids_net, self.photo_devant, self.photo_derriere, self.photo_interieur]
        self.statut = 'empote' if all(requis) else 'non_empote'
        self.save(update_fields=['statut'])


# =============================================================================
# ISO TANKS
# =============================================================================


class ISOTanks(ConteneurCommunMixin):
    """ISO Tank : conteneur avec ses champs propres (plombs amateurs/oils)."""

    def clean(self):
        if self.reference and Flexitanks.objects.filter(reference=self.reference).exists():
            raise ValidationError(
                "Cette référence est déjà utilisée par un Flexitank : "
                "la référence d'un conteneur doit être unique tous types confondus."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # plombs amateurs
    plombAmateur1      = models.CharField(max_length=50, blank=True, null=True)
    plombAmateur2      = models.CharField(max_length=50, blank=True, null=True)
    plombAmateur3      = models.CharField(max_length=50, blank=True, null=True)
    photoPlombAmateur1 = WebPImageField(upload_to='isotanks/plombs/', blank=True, null=True)
    photoPlombAmateur2 = WebPImageField(upload_to='isotanks/plombs/', blank=True, null=True)
    photoPlombAmateur3 = WebPImageField(upload_to='isotanks/plombs/', blank=True, null=True)

    #plombs oils
    photo_plombs_oils1 = WebPImageField(upload_to='conteneurs/plombs_oils1/', blank=True, null=True)
    Plombs_oils1         = models.CharField(
        max_length=200, blank=True, null=True,
        help_text="Numéros de plombs ",
    )
    photo_plombs_oils2 = WebPImageField(upload_to='conteneurs/plombs_oils2/', blank=True, null=True)
    Plombs_oils2       = models.CharField(
        max_length=200, blank=True, null=True,
        help_text="Numéros de plombs  ",
    )


    class Meta:
        verbose_name        = "ISO Tank"
        verbose_name_plural = "ISO Tanks"
        ordering            = ['reference']

    def __str__(self):
        return f"ISO Tank — {self.reference}"


# =============================================================================
# FLEXITANKS
# =============================================================================

class Flexitanks(ConteneurCommunMixin):
    """Flexitank : conteneur avec ses champs propres (heating pad, plombs)."""

    poids_brute       = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), blank=True, null=True)
    poids_equipements = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), blank=True, null=True)

    def clean(self):
        if self.reference and ISOTanks.objects.filter(reference=self.reference).exists():
            raise ValidationError(
                "Cette référence est déjà utilisée par un ISO Tank : "
                "la référence d'un conteneur doit être unique tous types confondus."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    Numeroheatingpad     = models.CharField(max_length=50, blank=True, null=True)
    Photoheatingpad      = WebPImageField(upload_to='flexitanks/heatingpad/',      blank=True, null=True)
    photoFlextank        = WebPImageField(upload_to='flexitanks/photos/',          blank=True, null=True)
    numeroFlextank       = models.CharField(max_length=50, blank=True, null=True)
    plombs_amateur       = models.CharField(
        max_length=200, blank=True, null=True,
        help_text="Numéros de plombs amateur  ",
    )
    plombs_amateur_photo = WebPImageField(upload_to='flexitanks/plombs_amateur/', blank=True, null=True)

    photo_plombs_oils = WebPImageField(upload_to='conteneurs/plombs_oils/', blank=True, null=True)
    Plombs_oils       = models.CharField(
        max_length=200, blank=True, null=True,
        help_text="Numéros de plombs ",
    )

    class Meta:
        verbose_name        = "Flexitank"
        verbose_name_plural = "Flexitanks"
        ordering            = ['reference']

    def __str__(self):
        return f"Flexitank {self.numeroFlextank or '—'} — {self.reference}"
