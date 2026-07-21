from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'content_type', 'object_repr', 'actor_username', 'ip_address')
    list_filter = ('action', 'content_type')
    search_fields = ('object_repr', 'actor_username', 'object_id')
    date_hierarchy = 'created_at'
    readonly_fields = [field.name for field in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
