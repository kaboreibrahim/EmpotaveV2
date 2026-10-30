from django.contrib import admin
from safedelete.admin import SafeDeleteAdmin, SafeDeleteAdminFilter, highlight_deleted

from .models import CompteurFacture, Facture, LigneFacture, fmt_milliers


class LigneFactureInline(admin.TabularInline):
    model = LigneFacture
    extra = 1
    fields = ("ordre", "designation", "tva_taux", "pu_ht", "quantite", "total_ht_affiche")
    readonly_fields = ("total_ht_affiche",)

    @admin.display(description="Total HT (FCFA)")
    def total_ht_affiche(self, obj):
        return fmt_milliers(obj.total_ht) if obj.pk else "—"


@admin.register(Facture)
class FactureAdmin(SafeDeleteAdmin):
    list_display = (
        highlight_deleted, "numero", "numero_proforma", "statut", "ref_client", "client",
        "date_facturation", "date_echeance", "total_ttc_fcfa_affiche", "total_ttc_eur_affiche",
    )
    list_filter = (SafeDeleteAdminFilter, "statut", "date_facturation", "incoterm", "banque")
    search_fields = ("numero", "numero_proforma", "ref_client", "ref_dossier")
    date_hierarchy = "date_facturation"
    inlines = [LigneFactureInline]
    actions = ["valider_proformas"]
    readonly_fields = (
        "numero", "numero_proforma", "statut", "date_validation", "date_echeance",
        "texte_incoterm",
        "total_ht_fcfa_affiche", "total_ttc_fcfa_affiche",
        "total_ht_eur_affiche", "total_ttc_eur_affiche",
    )
    fieldsets = (
        ("En-tête", {"fields": (
            "statut", "numero_proforma", "numero", "date_validation",
            "ref_client", "client", "date_facturation", "date_echeance",
        )}),
        ("Ligne Incoterm", {"fields": (
            "incoterm", "quantite_unites", "conditionnement", "produit", "usine",
            "port_livraison", "destination", "pu_fcfa_unite", "ref_dossier",
            "texte_incoterm",
        )}),
        ("Règlement", {"fields": ("conditions_reglement", "banque")}),
        ("Totaux", {"fields": (
            "taux_change",
            "total_ht_fcfa_affiche", "total_ttc_fcfa_affiche",
            "total_ht_eur_affiche", "total_ttc_eur_affiche",
        )}),
    )

    @admin.action(description="Valider (client) les proformas sélectionnées")
    def valider_proformas(self, request, queryset):
        proformas = queryset.filter(statut=Facture.Statut.PROFORMA)
        for facture in proformas:
            facture.valider()
        self.message_user(request, f"{len(proformas)} proforma(s) validée(s).")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "client", "banque", "produit", "port_livraison", "destination",
        ).prefetch_related("lignes")

    @admin.display(description="Total HT (FCFA)")
    def total_ht_fcfa_affiche(self, obj):
        return f"{fmt_milliers(obj.total_ht_fcfa)} FCFA" if obj.pk else "—"

    @admin.display(description="Total TTC (FCFA)")
    def total_ttc_fcfa_affiche(self, obj):
        return f"{fmt_milliers(obj.total_ttc_fcfa)} FCFA" if obj.pk else "—"

    @admin.display(description="Total HT (EUR)")
    def total_ht_eur_affiche(self, obj):
        return f"{obj.total_ht_eur:,.2f} EUR".replace(",", " ") if obj.pk else "—"

    @admin.display(description="Total TTC (EUR)")
    def total_ttc_eur_affiche(self, obj):
        return f"{obj.total_ttc_eur:,.2f} EUR".replace(",", " ") if obj.pk else "—"


@admin.register(CompteurFacture)
class CompteurFactureAdmin(admin.ModelAdmin):
    """Lecture seule : le compteur est géré automatiquement."""
    list_display = ("cle", "dernier_numero")
    readonly_fields = ("cle", "dernier_numero")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False