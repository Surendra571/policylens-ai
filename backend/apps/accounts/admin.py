from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "username", "is_staff", "is_active", "created_at")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("email", "username")
    ordering = ("-created_at",)

