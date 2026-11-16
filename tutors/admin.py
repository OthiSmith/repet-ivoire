from django.contrib import admin

from .models import TutorDocument, TutorProfile


class TutorDocumentInline(admin.TabularInline):
    model = TutorDocument
    extra = 0
    readonly_fields = ["kind", "original_name", "uploaded_at"]
    fields = ["kind", "original_name", "uploaded_at"]
    can_delete = False


@admin.register(TutorProfile)
class TutorProfileAdmin(admin.ModelAdmin):
    list_display = ["__str__", "status", "education", "experience_years", "is_available", "submitted_at"]
    list_filter = ["status", "education", "is_available", "communes__city"]
    search_fields = ["user__first_name", "user__last_name", "user__email", "user__phone"]
    filter_horizontal = ["subjects", "levels", "communes"]
    readonly_fields = ["submitted_at", "verified_at", "verified_by", "created_at", "updated_at"]
    inlines = [TutorDocumentInline]
