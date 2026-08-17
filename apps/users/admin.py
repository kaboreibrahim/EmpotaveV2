from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    Agent_empotage,
    Agent_selection,
    Client,
    CodeVerication,
    Personnel,
    PersonnelComptable,
    Users,
)


@admin.register(Users)
class UsersAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "user_type",
        "entreprise",
        "is_verified",
        "is_online",
        "is_staff",
        "is_active",
    )
    list_filter = (
        "user_type",
        "entreprise",
        "is_verified",
        "is_online",
        "is_staff",
        "is_active",
        "date_created",
    )
    search_fields = ("username", "email", "first_name", "last_name", "numero")
    ordering = ("username",)
    readonly_fields = ("date_created", "last_login", "date_joined")
    autocomplete_fields = ("pays", "entreprise")
    fieldsets = UserAdmin.fieldsets + (
        (
            "Informations metier",
            {
                "fields": (
                    "numero",
                    "photo",
                    "user_type",
                    "entreprise",
                    "pays",
                    "is_verified",
                    "is_online",
                    "date_created",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Informations metier",
            {
                "fields": (
                    "email",
                    "numero",
                    "photo",
                    "user_type",
                    "entreprise",
                    "pays",
                    "is_verified",
                )
            },
        ),
    )


@admin.register(CodeVerication)
class CodeVericationAdmin(admin.ModelAdmin):
    list_display = ("user", "typecode", "code", "date_created")
    list_filter = ("typecode", "date_created")
    search_fields = ("user__username", "user__email", "code")
    readonly_fields = ("Id_Verication", "date_created")
    autocomplete_fields = ("user",)


class UserWrapperAdmin(admin.ModelAdmin):
    list_display = ("user", "date_created")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")
    readonly_fields = ("id", "date_created")
    autocomplete_fields = ("user",)


@admin.register(Personnel)
class PersonnelAdmin(UserWrapperAdmin):
    pass


@admin.register(Client)
class ClientAdmin(UserWrapperAdmin):
    pass


@admin.register(Agent_selection)
class AgentSelectionAdmin(UserWrapperAdmin):
    pass


@admin.register(Agent_empotage)
class AgentEmpotageAdmin(UserWrapperAdmin):
    pass


@admin.register(PersonnelComptable)
class PersonnelComptableAdmin(UserWrapperAdmin):
    pass
