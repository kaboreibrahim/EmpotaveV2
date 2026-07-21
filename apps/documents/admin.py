from django.contrib import admin

from .models import Document, TypeDocument


@admin.register(TypeDocument)
class TypeDocumentAdmin(admin.ModelAdmin):
    list_display = ("type_document",)
    search_fields = ("type_document",)
    readonly_fields = ("Id_TypeDocument",)
    ordering = ("type_document",)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("type_document", "dossier", "statut", "date_modifier", "date_created")
    list_filter = ("statut", "type_document", "date_created", "date_modifier")
    search_fields = ("dossier__TRD", "dossier__projet", "type_document__type_document")
    readonly_fields = ("id", "date_created", "date_modifier")
    autocomplete_fields = ("dossier", "type_document")
    date_hierarchy = "date_created"
    ordering = ("-date_created",)
