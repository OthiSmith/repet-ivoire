"""Espace répétiteur : tableau de bord, profil, justificatifs."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView, UpdateView

from accounts.permissions import TutorRequiredMixin
from tutoring.models import Proposal
from tutoring.services import expire_overdue_proposals

from .forms import TutorDocumentForm, TutorProfileForm
from .models import TutorDocument, TutorProfile
from .services import ProfileError, submit_profile


class TutorProfileMixin(TutorRequiredMixin):
    """Fournit `self.profile`, créé au premier passage du répétiteur."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_tutor:
            self.profile, _ = TutorProfile.objects.get_or_create(user=request.user)
        return super().dispatch(request, *args, **kwargs)


class DashboardView(TutorProfileMixin, TemplateView):
    template_name = "tutors/dashboard.html"

    def get_context_data(self, **kwargs):
        expire_overdue_proposals()
        context = super().get_context_data(**kwargs)
        proposals = self.profile.proposals.select_related("request__level", "request__commune")
        context.update(
            profile=self.profile,
            missing=self.profile.missing_items(),
            pending_proposals=proposals.filter(status=Proposal.Status.PENDING),
            accepted_proposals=proposals.filter(status=Proposal.Status.ACCEPTED),
            students=proposals.filter(status=Proposal.Status.CHOSEN),
        )
        return context


class ProfileEditView(TutorProfileMixin, UpdateView):
    form_class = TutorProfileForm
    template_name = "tutors/profile_form.html"
    success_url = reverse_lazy("tutors:dashboard")

    def get_object(self, queryset=None):
        return self.profile

    def get(self, request, *args, **kwargs):
        if not self.profile.can_be_edited:
            messages.info(request, "Votre profil est en cours de vérification : il ne peut pas être modifié pour l'instant.")
            return redirect("tutors:dashboard")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if not self.profile.can_be_edited:
            return redirect("tutors:dashboard")
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Votre profil a été enregistré.")
        return super().form_valid(form)


class DocumentsView(TutorProfileMixin, View):
    template_name = "tutors/documents.html"

    def get(self, request):
        return self.render(TutorDocumentForm())

    def post(self, request):
        if not self.profile.can_be_edited:
            messages.error(request, "Votre profil est en cours de vérification : attendez la réponse de l'équipe.")
            return redirect("tutors:documents")
        form = TutorDocumentForm(request.POST, request.FILES)
        if not form.is_valid():
            return self.render(form)
        document = form.save(commit=False)
        document.tutor = self.profile
        document.original_name = request.FILES["file"].name[:255]
        document.save()
        messages.success(request, "Justificatif ajouté.")
        return redirect("tutors:documents")

    def render(self, form):
        return render(self.request, self.template_name, {
            "form": form, "profile": self.profile, "documents": self.profile.documents.all(),
        })


class DocumentDeleteView(TutorProfileMixin, View):
    def post(self, request, pk):
        document = get_object_or_404(TutorDocument, pk=pk, tutor=self.profile)
        if self.profile.status not in (TutorProfile.Status.DRAFT, TutorProfile.Status.REJECTED):
            messages.error(request, "Ce justificatif ne peut plus être supprimé.")
        else:
            document.file.delete(save=False)
            document.delete()
            messages.success(request, "Justificatif supprimé.")
        return redirect("tutors:documents")


class SubmitProfileView(TutorProfileMixin, View):
    def post(self, request):
        try:
            submit_profile(self.profile)
        except ProfileError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Profil envoyé ! Notre équipe va vérifier vos informations.")
        return redirect("tutors:dashboard")


class DocumentFileView(LoginRequiredMixin, View):
    """Affiche un justificatif : réservé à son propriétaire et à l'équipe."""

    def get(self, request, pk):
        document = get_object_or_404(TutorDocument.objects.select_related("tutor"), pk=pk)
        user = request.user
        is_owner = document.tutor.user_id == user.pk
        if not (is_owner or user.is_platform_admin or user.is_staff):
            raise Http404
        try:
            handle = document.file.open("rb")
        except FileNotFoundError:
            raise Http404
        response = FileResponse(handle, filename=document.original_name or document.file.name)
        response["Cache-Control"] = "private, no-store"
        return response
