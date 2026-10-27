from django.contrib import admin

from .models import (
    Commodite,
    CompagnieMaritime,
    Pays,
    POD,
    POL,
    SiteEmpotage,
    SiteSelection,
)


@admin.register(Pays)
class PaysAdmin(admin.ModelAdmin):
    list_display = ("nom", "date_created")
    search_fields = ("nom",)
    readonly_fields = ("id", "date_created")
    ordering = ("nom",)


@admin.register(Commodite)
class CommoditeAdmin(admin.ModelAdmin):
    list_display = ("nom", "sig", "Id_Pays", "date_created")
    list_filter = ("Id_Pays",)
    search_fields = ("nom", "sig", "Id_Pays__nom")
    readonly_fields = ("id", "date_created")
    autocomplete_fields = ("Id_Pays",)
    ordering = ("nom",)


class PortAdmin(admin.ModelAdmin):
    list_display = ("nom", "lieu", "Id_Pays", "date_created")
    list_filter = ("Id_Pays",)
    search_fields = ("nom", "lieu", "Id_Pays__nom")
    readonly_fields = ("id", "date_created")
    autocomplete_fields = ("Id_Pays",)


@admin.register(POL)
class POLAdmin(PortAdmin):
    pass


@admin.register(POD)
class PODAdmin(PortAdmin):
    pass


@admin.register(CompagnieMaritime)
class CompagnieMaritimeAdmin(PortAdmin):
    pass


class SiteAdmin(admin.ModelAdmin):
    list_display = ("nom", "lieu", "contact", "Id_Pays", "date_created")
    list_filter = ("Id_Pays",)
    search_fields = ("nom", "lieu", "contact", "Id_Pays__nom")
    readonly_fields = ("id", "date_created")
    autocomplete_fields = ("Id_Pays",)


@admin.register(SiteSelection)
class SiteSelectionAdmin(SiteAdmin):
    pass


@admin.register(SiteEmpotage)
class SiteEmpotageAdmin(SiteAdmin):
    pass


from django.contrib import admin
from safedelete.admin import SafeDeleteAdmin, SafeDeleteAdminFilter, highlight_deleted

from .models import Banque


@admin.register(Banque)
class BanqueAdmin(SafeDeleteAdmin):
    list_display = (highlight_deleted, "nom", "numero_compte", "titulaire", "bic_swift", "actif")
    list_filter = (SafeDeleteAdminFilter, "actif")
    search_fields = ("nom", "numero_compte", "titulaire", "iban", "bic_swift")
    fieldsets = (
        ("Banque", {"fields": ("nom", "titulaire", "actif")}),
        ("Coordonnées bancaires", {"fields": ("numero_compte", "iban", "bic_swift")}),
    )