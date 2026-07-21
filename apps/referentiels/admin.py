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
