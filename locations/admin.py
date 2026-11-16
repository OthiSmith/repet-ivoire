from django.contrib import admin

from .models import City, Commune


class CommuneInline(admin.TabularInline):
    model = Commune
    extra = 0
    prepopulated_fields = {"slug": ["name"]}


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ["name", "order"]
    list_editable = ["order"]
    prepopulated_fields = {"slug": ["name"]}
    inlines = [CommuneInline]


@admin.register(Commune)
class CommuneAdmin(admin.ModelAdmin):
    list_display = ["name", "city", "is_active"]
    list_filter = ["city", "is_active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}
