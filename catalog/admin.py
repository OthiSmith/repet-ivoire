from django.contrib import admin

from .models import Level, Subject


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ["name", "cycle", "exam", "order"]
    list_filter = ["cycle"]
    list_editable = ["order"]
    prepopulated_fields = {"slug": ["name"]}


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ["name", "order", "is_active"]
    list_editable = ["order", "is_active"]
    prepopulated_fields = {"slug": ["name"]}
