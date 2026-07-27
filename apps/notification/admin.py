from django.contrib import admin

from .models import Notification, PushSubscription


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "titre", "type_notification", "short_message", "categorie", "is_read", "date_created")
    list_filter = ("is_read", "categorie", "type_notification", "date_created")
    search_fields = ("user__username", "user__email", "titre", "message", "dossier__TRD", "dossier__projet")
    readonly_fields = ("id", "date_created")
    autocomplete_fields = ("user", "dossier")
    date_hierarchy = "date_created"
    ordering = ("-date_created",)

    @admin.display(description="Message")
    def short_message(self, obj):
        return obj.message[:80]


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("utilisateur", "endpoint_court", "user_agent", "created_at")
    list_filter = ("created_at",)
    search_fields = ("utilisateur__username", "utilisateur__email", "endpoint", "user_agent")
    readonly_fields = ("id", "created_at")
    autocomplete_fields = ("utilisateur",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    @admin.display(description="Endpoint")
    def endpoint_court(self, obj):
        return obj.endpoint[:70]
