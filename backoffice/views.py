"""Back-office métier : vérification des répétiteurs et traitement des demandes."""
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from accounts.permissions import PlatformAdminRequiredMixin
from tutoring.models import Proposal, TutoringRequest
from tutoring.services import (
    ActionError,
    close_request,
    expire_overdue_proposals,
    propose_tutor,
    suggest_tutors,
    withdraw_proposal,
)
from tutors.models import TutorProfile
from tutors.services import ProfileError, approve_profile, reject_profile


class DashboardView(PlatformAdminRequiredMixin, TemplateView):
    template_name = "backoffice/dashboard.html"

    def get_context_data(self, **kwargs):
        expire_overdue_proposals()
        context = super().get_context_data(**kwargs)
        requests = TutoringRequest.objects.select_related("level", "commune", "parent")
        context.update(
            pending_tutors=TutorProfile.objects.filter(status=TutorProfile.Status.PENDING).select_related("user"),
            new_requests=requests.filter(status=TutoringRequest.Status.NEW),
            # Demandes en cours sans aucune proposition active : il faut relancer la recherche.
            stalled_requests=requests.filter(status=TutoringRequest.Status.SEARCHING).annotate(
                active=Count("proposals", filter=Q(proposals__status__in=Proposal.ACTIVE_STATUSES))
            ).filter(active=0),
            stats={
                "verified_tutors": TutorProfile.objects.verified().count(),
                "open_requests": requests.filter(status__in=TutoringRequest.OPEN_STATUSES).count(),
                "matches": requests.filter(status=TutoringRequest.Status.MATCHED).count(),
            },
        )
        return context


class TutorListView(PlatformAdminRequiredMixin, ListView):
    template_name = "backoffice/tutor_list.html"
    context_object_name = "tutors"
    paginate_by = 30

    def get_queryset(self):
        queryset = TutorProfile.objects.select_related("user").order_by("-submitted_at", "-created_at")
        self.status = self.request.GET.get("statut", TutorProfile.Status.PENDING)
        if self.status in TutorProfile.Status.values:
            queryset = queryset.filter(status=self.status)
        search = self.request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search) | Q(user__phone__icontains=search))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = TutorProfile.Status.choices
        context["current_status"] = self.status
        return context


class TutorReviewView(PlatformAdminRequiredMixin, DetailView):
    template_name = "backoffice/tutor_review.html"
    context_object_name = "profile"
    queryset = TutorProfile.objects.select_related("user", "verified_by").prefetch_related(
        "subjects", "levels", "communes", "documents")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["proposals"] = self.object.proposals.select_related("request__level", "request__commune")[:20]
        return context

    def post(self, request, pk):
        profile = get_object_or_404(TutorProfile, pk=pk)
        try:
            if request.POST.get("decision") == "approve":
                approve_profile(profile, request.user)
                messages.success(request, f"Le profil de {profile} est validé.")
            else:
                reject_profile(profile, request.user, request.POST.get("reason", ""))
                messages.success(request, f"Le profil de {profile} a été renvoyé pour correction.")
        except ProfileError as error:
            messages.error(request, str(error))
        return redirect("backoffice:tutor_review", pk=pk)


class RequestListView(PlatformAdminRequiredMixin, ListView):
    template_name = "backoffice/request_list.html"
    context_object_name = "requests"
    paginate_by = 30

    def get_queryset(self):
        queryset = TutoringRequest.objects.select_related("level", "commune", "parent").annotate(
            accepted=Count("proposals", filter=Q(proposals__status=Proposal.Status.ACCEPTED)),
            pending=Count("proposals", filter=Q(proposals__status=Proposal.Status.PENDING)),
        )
        self.status = self.request.GET.get("statut", "OPEN")
        if self.status == "OPEN":
            queryset = queryset.filter(status__in=TutoringRequest.OPEN_STATUSES)
        elif self.status in TutoringRequest.Status.values:
            queryset = queryset.filter(status=self.status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = [("OPEN", "Ouvertes")] + list(TutoringRequest.Status.choices)
        context["current_status"] = self.status
        return context


class RequestDetailView(PlatformAdminRequiredMixin, DetailView):
    template_name = "backoffice/request_detail.html"
    context_object_name = "tutoring_request"
    queryset = TutoringRequest.objects.select_related("level", "commune", "parent").prefetch_related("subjects")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["proposals"] = self.object.proposals.select_related("tutor__user")
        context["suggestions"] = suggest_tutors(self.object)[:15] if self.object.is_open else []
        return context

    def post(self, request, pk):
        tutoring_request = get_object_or_404(TutoringRequest, pk=pk)
        action = request.POST.get("action")
        try:
            if action == "propose":
                tutor = get_object_or_404(TutorProfile, pk=request.POST.get("tutor"))
                propose_tutor(tutoring_request, tutor, request.user)
                messages.success(request, f"{tutor} a été proposé. Il a été prévenu.")
            elif action == "withdraw":
                proposal = get_object_or_404(Proposal, pk=request.POST.get("proposal"), request=tutoring_request)
                withdraw_proposal(proposal)
                messages.success(request, "Proposition retirée.")
            elif action == "notes":
                tutoring_request.admin_notes = request.POST.get("admin_notes", "")
                tutoring_request.save(update_fields=["admin_notes", "updated_at"])
                messages.success(request, "Notes enregistrées.")
            elif action == "close":
                close_request(tutoring_request)
                messages.success(request, "Demande clôturée.")
        except ActionError as error:
            messages.error(request, str(error))
        return redirect("backoffice:request_detail", pk=pk)
