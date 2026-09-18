from django.contrib import admin
from .models import Clause


@admin.register(Clause)
class ClauseAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "policy", "page_number", "confidence", "created_at")
    list_filter = ("category", "confidence", "policy")
    search_fields = ("title", "explanation", "source_text", "section", "policy__name")
    date_hierarchy = "created_at"

