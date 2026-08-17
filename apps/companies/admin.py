from django.contrib import admin

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("nom", "slug", "couleur", "actif", "date_created")
    list_filter = ("actif",)
    search_fields = ("nom", "slug")
    prepopulated_fields = {"slug": ("nom",)}
    readonly_fields = ("id", "date_created")
    ordering = ("nom",)
