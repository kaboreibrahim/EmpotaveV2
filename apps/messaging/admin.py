from django.contrib import admin

from .models import (
    Conversation,
    ConversationMember,
    Group,
    Message,
    MessageAttachment,
    MessageRead,
)


class ConversationMemberInline(admin.TabularInline):
    model = ConversationMember
    extra = 0
    autocomplete_fields = ("user",)
    readonly_fields = ("date_ajout",)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("__str__", "type_conversation", "dossier", "date_created", "date_modifier")
    list_filter = ("type_conversation", "date_created")
    search_fields = ("titre", "dossier__TRD", "dossier__projet")
    readonly_fields = ("id", "date_created", "date_modifier")
    autocomplete_fields = ("dossier",)
    inlines = [ConversationMemberInline]


class MessageAttachmentInline(admin.TabularInline):
    model = MessageAttachment
    extra = 0
    readonly_fields = ("id", "date_created")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("__str__", "conversation", "auteur", "type_message", "est_supprime", "date_created")
    list_filter = ("type_message", "est_supprime", "date_created")
    search_fields = ("contenu", "auteur__username", "auteur__email", "conversation__titre")
    readonly_fields = ("id", "date_created", "date_modifier")
    autocomplete_fields = ("conversation", "auteur", "reponse_a")
    inlines = [MessageAttachmentInline]


@admin.register(MessageRead)
class MessageReadAdmin(admin.ModelAdmin):
    list_display = ("message", "user", "date_lecture")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("id", "date_lecture")
    autocomplete_fields = ("message", "user")


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("nom", "conversation", "cree_par", "date_created")
    search_fields = ("nom", "description")
    readonly_fields = ("id", "date_created")
    autocomplete_fields = ("conversation", "cree_par")
