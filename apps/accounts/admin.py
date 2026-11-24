"""Admin for the custom user: role and bio sit next to the usual fields."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "display_name", "is_staff")
    list_filter = ("role", "is_staff", "is_superuser")
    search_fields = ("username", "email", "display_name")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("TeachFlow", {"fields": ("role", "display_name", "bio")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("TeachFlow", {"fields": ("role", "display_name", "bio")}),
    )
