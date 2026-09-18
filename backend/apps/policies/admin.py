from django.contrib import admin

from .models import Policy


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "policy_type", "user", "status", "uploaded_at", "analyzed_at")
    list_filter = ("status", "policy_type", "provider")
    search_fields = ("name", "provider", "user__email", "user__username")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
