from django.contrib import admin
from safedelete.admin import SafeDeleteAdmin, SafeDeleteAdminFilter, highlight_deleted

from .models import CompteurFacture, Facture, Incoterm, LigneFacture, fmt_milliers


class LigneFactureInline(admin.TabularInline):
    model = LigneFacture
    extra = 1
    fields = ("designation", "tva_taux", "pu_ht", "quantite", "total_ht_affiche")
    readonly_fields = ("total_ht_affiche",)

    @admin.display(description="Total HT (FCFA)")
    def total_ht_affiche(self, obj):
        return fmt_milliers(obj.total_ht) if obj.pk else "—"


@admin.register(Incoterm)
class IncotermAdmin(SafeDeleteAdmin):
    list_display = (highlight_deleted, "code", "libelle")
    list_filter = (SafeDeleteAdminFilter,)
    search_fields = ("code", "libelle")
    ordering = ("code",)


@admin.register(Facture)
class FactureAdmin(SafeDeleteAdmin):
    list_display = (
        highlight_deleted, "numero", "ref_client", "client", "date_facturation",
        "date_echeance", "total_ttc_fcfa_affiche", "total_ttc_eur_affiche",
    )
    list_filter = (SafeDeleteAdminFilter, "date_facturation", "incoterm", "banque")
    search_fields = ("numero", "ref_client", "ref_dossier", "client__nom")
    date_hierarchy = "date_facturation"
    inlines = [LigneFactureInline]
    readonly_fields = (
        "numero", "date_echeance", "texte_incoterm",
        "total_ht_fcfa_affiche", "total_ttc_fcfa_affiche",
        "total_ht_eur_affiche", "total_ttc_eur_affiche",
    )
    fieldsets = (
        ("En-tête", {"fields": (
            "numero", "ref_client", "client", "date_facturation", "date_echeance",
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

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "client", "banque", "incoterm", "produit", "port_livraison", "destination",
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
class CompteurFactureAdmin(SafeDeleteAdmin):
    """Lecture seule : le compteur est géré automatiquement."""
    list_display = (highlight_deleted, "cle", "dernier_numero")
    readonly_fields = ("cle", "dernier_numero")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False