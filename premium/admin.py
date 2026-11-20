from django.contrib import admin

from .models import CurriculumUnit, Grade, PlanItem, Session, Subscription


@admin.register(CurriculumUnit)
class CurriculumUnitAdmin(admin.ModelAdmin):
    list_display = ["title", "level", "subject", "term", "order"]
    list_filter = ["level", "subject", "term"]
    list_editable = ["order"]
    search_fields = ["title"]


class PlanItemInline(admin.TabularInline):
    model = PlanItem
    extra = 0


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["__str__", "status", "starts_on", "ends_on", "amount", "payment_method"]
    list_filter = ["status", "payment_method"]
    raw_id_fields = ["request", "activated_by"]
    inlines = [PlanItemInline]


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ["__str__", "subscription", "parent_status", "parent_issue"]
    list_filter = ["status", "parent_status", "parent_issue"]
    raw_id_fields = ["subscription", "declared_by"]


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ["__str__", "subscription", "date", "kind"]
    raw_id_fields = ["subscription", "added_by"]
