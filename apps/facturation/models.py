"""
Facturation OOA — modèles Django (version corrigée de ta version).

HYPOTHESES à vérifier :
- 'clients.Client', 'banques.Banque', 'referentiels.Commodite',
  'referentiels.POL' et 'referentiels.POD' existent déjà.
- Compteur de numérotation continu sur l'année (IN + AAMM + compteur).
  Pour une remise à zéro mensuelle : cle = f"{date:%Y%m}" dans prochain_numero.
- TimestampMixin fournit déjà created_at / updated_at.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import IntegrityError, models, transaction
from django.utils import timezone
from django_lifecycle import LifecycleModel
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE

from core.mixins import TimestampMixin

PARITE_XOF_EUR = Decimal("655.957")  # parité fixe XOF/EUR
DELAI_ECHEANCE_JOURS = 15

# conditionnement -> (singulier, pluriel) pour le texte de la ligne Incoterm
UNITES = {
    "FLEXITANKS": ("Flexitank", "Flexitanks"),
    "ISO_TANKS": ("Iso", "Isos"),
}


def fmt_milliers(valeur):
    """818634 -> '818 634'."""
    return f"{int(valeur):,}".replace(",", " ")


def _de(nom):
    """'Abidjan' -> "d'Abidjan" ; 'San Pedro' -> 'de San Pedro'."""
    return f"d'{nom}" if nom[:1].lower() in "aeiouyéèêâîô" else f"de {nom}"


class CompteurFacture(TimestampMixin):
    """Compteur technique : jamais supprimé (pas de soft delete), sinon get_or_create
    ne le verrait plus et recréerait la même clé -> IntegrityError."""
    cle = models.CharField(max_length=6, unique=True)
    dernier_numero = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.cle} : {self.dernier_numero}"

    @classmethod
    def prochain_numero(cls, date, prefixe="IN"):
        """IN2610-0001 pour une facture, PF2610-0001 pour une proforma (compteurs séparés)."""
        cle = f"{date.year}" if prefixe == "IN" else f"{prefixe}{date.year}"
        # Crée la ligne de l'année si besoin ; si deux créations simultanées se croisent,
        # la seconde échoue sur l'unicité et on récupère simplement la ligne existante.
        try:
            with transaction.atomic():
                cls.objects.get_or_create(cle=cle)
        except IntegrityError:
            pass
        with transaction.atomic():
            compteur = cls.objects.select_for_update().get(cle=cle)
            compteur.dernier_numero += 1
            compteur.save(update_fields=["dernier_numero"])
        return f"{prefixe}{date:%y%m}-{compteur.dernier_numero:04d}"


class Incoterm(SafeDeleteModel, LifecycleModel, TimestampMixin):
    """Incoterm (ex. FOB, CIF) — alimente la liste déroulante."""
    code = models.CharField(max_length=10, unique=True)
    libelle = models.CharField(max_length=100)

    def __str__(self):
        return self.code


class Facture(SafeDeleteModel, LifecycleModel, TimestampMixin):
    """Créée en PROFORMA (n° PF…), elle devient FACTURE (n° IN…) quand le client valide."""
    _safedelete_policy = SOFT_DELETE_CASCADE  # supprime aussi les lignes (soft)

    class Statut(models.TextChoices):
        PROFORMA = "PROFORMA", "Proforma"
        FACTURE = "FACTURE", "Facture"

    statut = models.CharField(
        max_length=10, choices=Statut.choices, default=Statut.PROFORMA, editable=False,
    )
    date_validation = models.DateTimeField(null=True, blank=True, editable=False)

    # --- En-tête ---
    numero_proforma = models.CharField(max_length=15, unique=True, null=True, editable=False)
    numero = models.CharField(max_length=15, unique=True, null=True, editable=False)  # attribué à la validation
    ref_client = models.CharField(max_length=30)  # TR fourni par le client, saisi à la main
    date_facturation = models.DateField(default=timezone.localdate)
    date_echeance = models.DateField(editable=False)
    client = models.ForeignKey("users.Client", on_delete=models.PROTECT)
    banque = models.ForeignKey("referentiels.Banque", on_delete=models.PROTECT)
    conditions_reglement = models.CharField(max_length=100, default="À réception")

    # --- Ligne Incoterm ---
    incoterm = models.ForeignKey(Incoterm, on_delete=models.PROTECT)
    quantite_unites = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    conditionnement = models.CharField(
        max_length=20, default="ISO_TANKS",
        choices=[("FLEXITANKS", "Flexitanks"), ("ISO_TANKS", "ISO Tanks")],
    )
    produit = models.ForeignKey("referentiels.Commodite", on_delete=models.PROTECT)
    usine = models.CharField(max_length=100, blank=True)  # COPROIL
    port_livraison = models.ForeignKey("referentiels.POL", on_delete=models.PROTECT)
    pu_fcfa_unite = models.DecimalField(
        max_digits=14, decimal_places=0, validators=[MinValueValidator(0)],
    )
    ref_dossier = models.CharField(max_length=30, blank=True)  # PJ2605-0231
    destination = models.ForeignKey("referentiels.POD", on_delete=models.PROTECT)

    taux_change = models.DecimalField(
        max_digits=10, decimal_places=3, default=PARITE_XOF_EUR,
        validators=[MinValueValidator(Decimal("0.001"))],  # évite la division par zéro dans en_euro
    )

    class Meta:
        ordering = ["-date_facturation", "-date_created"]

    def save(self, *args, **kwargs):
        if not self.numero_proforma and not self.numero:
            self.numero_proforma = CompteurFacture.prochain_numero(self.date_facturation, "PF")
        self.date_echeance = self.date_facturation + timedelta(days=DELAI_ECHEANCE_JOURS)
        super().save(*args, **kwargs)

    # --- Cycle de vie ---
    @property
    def est_proforma(self):
        return self.statut == self.Statut.PROFORMA

    @property
    def reference(self):
        """N° affiché : n° de facture une fois validée, sinon n° de proforma."""
        return self.numero or self.numero_proforma

    def valider(self):
        """Validation client : la proforma devient facture (n° IN…, datée du jour)."""
        if not self.est_proforma:
            raise ValueError(f"{self.reference} est déjà une facture.")
        with transaction.atomic():
            self.date_facturation = timezone.localdate()
            self.numero = CompteurFacture.prochain_numero(self.date_facturation)
            self.statut = self.Statut.FACTURE
            self.date_validation = timezone.now()
            self.save()

    # --- Totaux ---
    @property
    def total_ht_fcfa(self):
        return sum((l.total_ht for l in self.lignes.all()), Decimal("0"))

    @property
    def total_ttc_fcfa(self):
        return sum((l.total_ttc for l in self.lignes.all()), Decimal("0"))

    def en_euro(self, montant_fcfa):
        return (montant_fcfa / self.taux_change).quantize(Decimal("0.01"), ROUND_HALF_UP)

    @property
    def total_ht_eur(self):
        return self.en_euro(self.total_ht_fcfa)

    @property
    def total_ttc_eur(self):
        return self.en_euro(self.total_ttc_fcfa)

    # --- Texte Incoterm généré ---
    @property
    def texte_incoterm(self):
        # Facture pas encore remplie (ex. page d'ajout de l'admin) : rien à afficher
        if (
            self.quantite_unites is None
            or self.pu_fcfa_unite is None
            or not all([
                self.incoterm_id, self.produit_id,
                self.port_livraison_id, self.destination_id,
            ])
        ):
            return "—"
        singulier, pluriel = UNITES.get(self.conditionnement, ("unité", "unités"))
        unite = pluriel if self.quantite_unites > 1 else singulier
        pu_eur = self.en_euro(self.pu_fcfa_unite).quantize(Decimal("1"), ROUND_HALF_UP)
        total_eur = pu_eur * self.quantite_unites
        designation = " ".join(filter(None, [
            f"{self.quantite_unites:02d}", unite, "STC", str(self.produit),
            f"depuis usine de {self.usine}" if self.usine else "",
        ]))
        return (
            f"Incoterm : {self.incoterm} - {designation} "
            f"rendu port {_de(str(self.port_livraison))} "
            f"pour un montant de {fmt_milliers(self.pu_fcfa_unite)} FCFA/{singulier} "
            f"soit {fmt_milliers(pu_eur)} EUR/{singulier} - {fmt_milliers(total_eur)} "
            f"{self.ref_client} {self.ref_dossier} "
            f"// {self.port_livraison} - {self.destination}"
        ).strip()

    def __str__(self):
        return self.reference or "—"


class LigneFacture(SafeDeleteModel, TimestampMixin):
    facture = models.ForeignKey(Facture, related_name="lignes", on_delete=models.CASCADE)
    designation = models.CharField(max_length=255)  # ex. MISE_A_FOB - MISE A FOB
    tva_taux = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    pu_ht = models.DecimalField(max_digits=14, decimal_places=0, validators=[MinValueValidator(0)])
    quantite = models.DecimalField(
        max_digits=10, decimal_places=2, default=1,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    def __str__(self):
        return self.designation

    # Le FCFA n'a pas de centimes : chaque total de ligne est arrondi à l'unité
    @property
    def total_ht(self):
        # Ligne vide (ex. formulaire d'ajout) : pas de calcul possible
        if self.pu_ht is None or self.quantite is None:
            return Decimal("0")
        return (self.pu_ht * self.quantite).quantize(Decimal("1"), ROUND_HALF_UP)

    @property
    def total_ttc(self):
        taux = self.tva_taux if self.tva_taux is not None else Decimal("0")
        return (self.total_ht * (1 + taux / 100)).quantize(Decimal("1"), ROUND_HALF_UP)