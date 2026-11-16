"""Administration technique (Django admin) des utilisateurs."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["email", "first_name", "last_name", "phone", "role", "is_active", "is_suspended", "date_joined"]
    list_filter = ["role", "is_active", "is_suspended", "is_staff"]
    search_fields = ["email", "phone", "first_name", "last_name"]
    readonly_fields = ["date_joined", "last_login"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Identité", {"fields": ("first_name", "last_name", "phone", "role")}),
        ("Statut", {"fields": ("is_active", "is_suspended", "suspension_reason")}),
        ("Permissions", {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "phone", "first_name", "last_name", "role", "password1", "password2"),
            },
        ),
    )
