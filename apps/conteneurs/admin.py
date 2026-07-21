from django.contrib import admin

from .models import Dossier, Flexitanks, ISOTanks


@admin.register(Dossier)
class DossierAdmin(admin.ModelAdmin):
    list_display = (
        "TRD",
        "projet",
        "Booking",
        "type_conteneur",
        "statut",
        "Id_Pays",
        "id_client",
        "date_created",
    )
    list_filter = (
        "statut",
        "type_conteneur",
        "Id_Pays",
        "Id_Commodite",
        "Id_CompagnieMaritime",
        "date_created",
    )
    search_fields = (
        "TRD",
        "projet",
        "Booking",
        "Id_Pays__nom",
        "id_client__user__username",
        "id_client__user__email",
    )
    readonly_fields = ("id", "date_created")
    autocomplete_fields = (
        "Id_Pays",
        "Id_POD",
        "Id_POL",
        "Id_Commodite",
        "Id_CompagnieMaritime",
        "Id_SiteSelection",
        "Id_SiteEmpotage",
        "Id_Agent_selection",
        "Id_Agent_empotage",
        "id_client",
        "Id_Personnel",
    )
    date_hierarchy = "date_created"
    ordering = ("-date_created",)


@admin.register(ISOTanks)
class ISOTanksAdmin(admin.ModelAdmin):
    list_display = ("reference", "dossier", "statut", "etat", "poids_net", "Temerature", "date_created")
    list_filter = ("statut", "etat", "date_created")
    search_fields = (
        "reference",
        "dossier__TRD",
        "dossier__projet",
        "Plombs_oils1",
        "Plombs_oils2",
        "plombAmateur1",
        "plombAmateur2",
        "plombAmateur3",
    )
    readonly_fields = ("id", "date_created")
    autocomplete_fields = ("dossier",)
    ordering = ("reference",)


@admin.register(Flexitanks)
class FlexitanksAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "dossier",
        "statut",
        "etat",
        "numeroFlextank",
        "Numeroheatingpad",
        "poids_brute",
        "poids_equipements",
        "date_created",
    )
    list_filter = ("statut", "etat", "date_created")
    search_fields = (
        "reference",
        "dossier__TRD",
        "dossier__projet",
        "numeroFlextank",
        "Numeroheatingpad",
        "Plombs_oils",
        "plombs_amateur",
    )
    readonly_fields = ("id", "date_created")
    autocomplete_fields = ("dossier",)
    ordering = ("reference",)
