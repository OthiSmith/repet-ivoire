"""Back-office métier : vérification des répétiteurs et traitement des demandes."""
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from accounts.permissions import PlatformAdminRequiredMixin
from catalog.models import Level, Subject
from premium import services as premium_services
from premium.forms import ActivationForm
from premium.models import CurriculumUnit, Session, Subscription
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
            premium_requests=Subscription.objects.filter(status=Subscription.Status.REQUESTED)
            .select_related("request__level", "request__commune", "request__parent"),
            premium_issues=Session.objects.filter(parent_status=Session.ParentStatus.DISPUTED)
            .select_related("subscription__request").order_by("-parent_responded_at")[:5],
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


# ---------------------------------------------------------------------------
# Suivi Premium
# ---------------------------------------------------------------------------
class PremiumListView(PlatformAdminRequiredMixin, ListView):
    template_name = "backoffice/premium_list.html"
    context_object_name = "subscriptions"
    paginate_by = 30

    def get_queryset(self):
        queryset = Subscription.objects.select_related("request__level", "request__commune", "request__parent")
        self.status = self.request.GET.get("statut", Subscription.Status.REQUESTED)
        if self.status in Subscription.Status.values:
            queryset = queryset.filter(status=self.status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Subscription.Status.choices
        context["current_status"] = self.status
        return context


class PremiumDetailView(PlatformAdminRequiredMixin, View):
    template_name = "backoffice/premium_detail.html"

    def get(self, request, pk, form=None):
        subscription = get_object_or_404(
            Subscription.objects.select_related("request__parent", "request__level", "request__commune"), pk=pk)
        return render(request, self.template_name, {
            "subscription": subscription,
            "form": form or ActivationForm(initial={"months": subscription.months_requested}),
            "stats": premium_services.attendance_stats(subscription) if subscription.starts_on else None,
            "issues": subscription.sessions.exclude(parent_issue="").order_by("-date")[:20],
        })

    def post(self, request, pk):
        subscription = get_object_or_404(Subscription, pk=pk)
        try:
            if request.POST.get("action") == "cancel":
                premium_services.cancel(subscription)
                messages.success(request, "Abonnement annulé.")
            else:
                form = ActivationForm(request.POST)
                if not form.is_valid():
                    return self.get(request, pk, form=form)
                premium_services.activate(subscription, request.user, **form.cleaned_data)
                messages.success(request, f"Suivi actif jusqu'au {subscription.ends_on:%d/%m/%Y}. La famille et le répétiteur sont prévenus.")
        except premium_services.PremiumError as error:
            messages.error(request, str(error))
        return redirect("backoffice:premium_detail", pk=pk)


class CurriculumView(PlatformAdminRequiredMixin, View):
    """Programme de référence par classe et matière, importé par les répétiteurs dans le plan des élèves."""

    template_name = "backoffice/curriculum.html"

    def get(self, request):
        levels, subjects = Level.objects.all(), Subject.objects.filter(is_active=True)
        level = levels.filter(pk=request.GET.get("niveau")).first() or levels.first()
        subject = subjects.filter(pk=request.GET.get("matiere")).first() or subjects.first()
        return render(request, self.template_name, {
            "levels": levels, "subjects": subjects, "level": level, "subject": subject,
            "units": CurriculumUnit.objects.filter(level=level, subject=subject),
            "terms": CurriculumUnit.Term.choices,
        })

    def post(self, request):
        level = get_object_or_404(Level, pk=request.POST.get("level"))
        subject = get_object_or_404(Subject, pk=request.POST.get("subject"))
        if request.POST.get("action") == "delete":
            CurriculumUnit.objects.filter(pk=request.POST.get("unit"), level=level, subject=subject).delete()
            messages.success(request, "Chapitre supprimé.")
        else:
            # Un chapitre par ligne : permet de coller tout un programme d'un coup.
            titles = [line.strip() for line in request.POST.get("titles", "").splitlines() if line.strip()]
            term = request.POST.get("term", "")
            term = term if term in CurriculumUnit.Term.values else ""
            start = CurriculumUnit.objects.filter(level=level, subject=subject).count()
            CurriculumUnit.objects.bulk_create([
                CurriculumUnit(level=level, subject=subject, title=title[:160], term=term, order=start + i)
                for i, title in enumerate(titles, start=1)
            ])
            messages.success(request, f"{len(titles)} chapitre(s) ajouté(s).")
        return redirect(f"{request.path}?niveau={level.pk}&matiere={subject.pk}")
