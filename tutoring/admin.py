from django.contrib import admin

from .models import Proposal, TutoringRequest


class ProposalInline(admin.TabularInline):
    model = Proposal
    extra = 0
    fields = ["tutor", "status", "created_at", "expires_at", "responded_at"]
    readonly_fields = ["created_at", "responded_at"]
    raw_id_fields = ["tutor"]


@admin.register(TutoringRequest)
class TutoringRequestAdmin(admin.ModelAdmin):
    list_display = ["__str__", "parent", "status", "created_at"]
    list_filter = ["status", "level__cycle", "commune__city"]
    search_fields = ["child_first_name", "parent__email", "parent__phone", "neighborhood"]
    raw_id_fields = ["parent"]
    inlines = [ProposalInline]


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ["__str__", "status", "created_at", "expires_at"]
    list_filter = ["status"]
    raw_id_fields = ["request", "tutor", "created_by"]
