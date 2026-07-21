from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "short_message", "is_read", "date_created")
    list_filter = ("is_read", "date_created")
    search_fields = ("user__username", "user__email", "message")
    readonly_fields = ("id", "date_created")
    autocomplete_fields = ("user",)
    date_hierarchy = "date_created"
    ordering = ("-date_created",)

    @admin.display(description="Message")
    def short_message(self, obj):
        return obj.message[:80]
