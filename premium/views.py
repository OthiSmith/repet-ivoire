"""Suivi Premium : offre, tableau de suivi, programme, cahier de séances, notes, rapport mensuel."""
from datetime import date, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView

from accounts.permissions import ParentRequiredMixin
from tutoring.models import TutoringRequest

from . import services
from .charts import grade_charts
from .forms import (
    GradeForm,
    MissedSessionForm,
    PlanItemForm,
    PremiumRequestForm,
    ReplacementForm,
    SessionForm,
    SessionResponseForm,
)
from .models import PlanItem, Session, Subscription
from .services import PremiumError


class PremiumInfoView(TemplateView):
    """Présentation publique de l'offre."""

    template_name = "premium/info.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(price=settings.PREMIUM_MONTHLY_PRICE, **kwargs)


class PremiumOfferView(ParentRequiredMixin, View):
    """Souscription du parent pour une mise en relation confirmée."""

    template_name = "premium/offer.html"

    def get_request(self, pk):
        return get_object_or_404(TutoringRequest.objects.select_related("level", "commune"),
                                 pk=pk, parent=self.request.user)

    def get(self, request, pk):
        tutoring_request = self.get_request(pk)
        return render(request, self.template_name, {
            "tutoring_request": tutoring_request,
            "subscription": Subscription.objects.filter(request=tutoring_request).first(),
            "form": PremiumRequestForm(),
            "price": settings.PREMIUM_MONTHLY_PRICE,
            "payment_instructions": settings.PREMIUM_PAYMENT_INSTRUCTIONS,
        })

    def post(self, request, pk):
        tutoring_request = self.get_request(pk)
        form = PremiumRequestForm(request.POST)
        if form.is_valid():
            try:
                services.request_premium(tutoring_request, request.user, form.cleaned_data["months"])
            except PremiumError as error:
                messages.error(request, str(error))
            else:
                messages.success(request, "Demande envoyée ! Notre équipe vous contacte pour le paiement.")
        return redirect("premium:offer", pk=pk)


# ---------------------------------------------------------------------------
# Accès au suivi
# ---------------------------------------------------------------------------
class SubscriptionAccessMixin(LoginRequiredMixin):
    """
    Charge l'abonnement et le rôle de l'utilisateur : « parent », « tutor » ou « admin ».

    `allowed_roles` restreint la vue ; les autres utilisateurs reçoivent une 404
    (on ne révèle pas l'existence du suivi).
    """

    allowed_roles = ("parent", "tutor", "admin")
    requires_current = False

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.subscription = get_object_or_404(
            Subscription.objects.select_related("request__parent", "request__level", "request__commune"),
            pk=kwargs["pk"])
        self.role = self.get_role(request.user)
        if self.role is None:
            raise Http404
        if self.role not in self.allowed_roles:
            raise PermissionDenied
        if self.role != "admin" and self.subscription.status != Subscription.Status.ACTIVE:
            # Pas encore activé (ou annulé) : retour à l'offre ou à l'espace.
            if self.role == "parent":
                return redirect("premium:offer", pk=self.subscription.request_id)
            raise Http404
        if self.requires_current and not self.subscription.is_current:
            messages.error(request, "Le suivi Premium n'est pas actif : il doit être renouvelé.")
            return redirect("premium:tracking", pk=self.subscription.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_role(self, user):
        if self.subscription.request.parent_id == user.pk:
            return "parent"
        tutor = self.subscription.tutor
        if tutor and tutor.user_id == user.pk and not user.is_suspended:
            return "tutor"
        if user.is_platform_admin or user.is_staff:
            return "admin"
        return None

    def base_context(self, **extra):
        return {"subscription": self.subscription, "tutoring_request": self.subscription.request,
                "role": self.role, **extra}


class FormPageView(SubscriptionAccessMixin, View):
    """Page contenant un seul formulaire (gabarit premium/form_page.html)."""

    form_class = None
    page_title = ""
    intro = ""
    submit_label = "Enregistrer"

    def get_form(self, data=None):
        return self.form_class(data, subscription=self.subscription)

    def get(self, request, pk):
        return self.render(self.get_form())

    def post(self, request, pk):
        form = self.get_form(request.POST)
        if not form.is_valid():
            return self.render(form)
        try:
            self.form_valid(form)
        except PremiumError as error:
            messages.error(request, str(error))
            return self.render(form)
        return redirect("premium:tracking", pk=self.subscription.pk)

    def render(self, form):
        return render(self.request, "premium/form_page.html", self.base_context(
            form=form, page_title=self.page_title, intro=self.intro, submit_label=self.submit_label))


# ---------------------------------------------------------------------------
# Tableau de suivi
# ---------------------------------------------------------------------------
class TrackingView(SubscriptionAccessMixin, TemplateView):
    template_name = "premium/tracking.html"

    def get_context_data(self, **kwargs):
        sub = self.subscription
        sessions = sub.sessions.prefetch_related("plan_items__subject")
        grades = sub.grades.select_related("subject")
        return super().get_context_data(**self.base_context(
            stats=services.attendance_stats(sub),
            progress=services.progress_by_subject(sub),
            awaiting=sessions.filter(status=Session.Status.DONE, parent_status=Session.ParentStatus.PENDING),
            recent_sessions=sessions[:5],
            charts=grade_charts(grades),
            recent_grades=grades.order_by("-date", "-pk")[:8],
            issue_choices=Session.Issue.choices,
        ), **kwargs)


class SessionListView(SubscriptionAccessMixin, TemplateView):
    template_name = "premium/sessions.html"

    def get_context_data(self, **kwargs):
        sessions = self.subscription.sessions.prefetch_related("plan_items__subject")
        return super().get_context_data(**self.base_context(
            sessions=sessions, issue_choices=Session.Issue.choices), **kwargs)


class SessionCreateView(FormPageView):
    allowed_roles = ("tutor",)
    requires_current = True
    form_class = SessionForm
    page_title = "Renseigner une séance"
    intro = "La famille reçoit une notification et confirme que la séance a bien eu lieu."

    def form_valid(self, form):
        services.declare_session(form, self.subscription, self.request.user)
        messages.success(self.request, "Séance enregistrée. La famille va la confirmer.")


class SessionRespondView(LoginRequiredMixin, View):
    def post(self, request, session_pk):
        session = get_object_or_404(Session.objects.select_related("subscription__request"), pk=session_pk,
                                    subscription__request__parent=request.user)
        form = SessionResponseForm(request.POST)
        form.is_valid()
        confirmed = request.POST.get("decision") == "confirm"
        try:
            services.respond_to_session(session, request.user, confirmed,
                                        form.cleaned_data.get("issue", ""), form.cleaned_data.get("comment", ""))
        except PremiumError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Merci, c'est noté." if confirmed else "Merci : notre équipe est prévenue.")
        next_url = request.POST.get("next", "")
        if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("premium:tracking", pk=session.subscription_id)


class MissedSessionView(FormPageView):
    allowed_roles = ("parent",)
    form_class = MissedSessionForm
    page_title = "Signaler une absence du répétiteur"
    intro = "Indiquez la date d'une séance prévue où le répétiteur n'est pas venu. Notre équipe est prévenue."
    submit_label = "Signaler l'absence"

    def form_valid(self, form):
        services.report_missed_session(self.subscription, self.request.user, form.cleaned_data["date"],
                                       form.cleaned_data["comment"])
        messages.success(self.request, "Absence signalée. Notre équipe va prendre contact avec vous.")


class ReplacementView(FormPageView):
    allowed_roles = ("parent",)
    requires_current = True
    form_class = ReplacementForm
    page_title = "Demander un remplacement"
    intro = ("Avantage Premium : votre demande est traitée en priorité. Notre équipe vous rappelle "
             "et vous propose un autre répétiteur si nécessaire.")
    submit_label = "Envoyer la demande"

    def get_form(self, data=None):
        return ReplacementForm(data)

    def form_valid(self, form):
        services.request_replacement(self.subscription, self.request.user, form.cleaned_data["message"])
        messages.success(self.request, "Demande envoyée en priorité à notre équipe.")


class GradeCreateView(FormPageView):
    allowed_roles = ("parent", "tutor")
    requires_current = True
    form_class = GradeForm
    page_title = "Ajouter une note"
    intro = "Notes obtenues à l'école (devoirs, interrogations, compositions) : elles permettent de mesurer les progrès."

    def form_valid(self, form):
        grade = form.save(commit=False)
        grade.subscription = self.subscription
        grade.added_by = self.request.user
        grade.save()
        messages.success(self.request, "Note ajoutée.")


# ---------------------------------------------------------------------------
# Programme (plan de travail)
# ---------------------------------------------------------------------------
class PlanView(SubscriptionAccessMixin, View):
    template_name = "premium/plan.html"

    def get(self, request, pk, form=None):
        items = self.subscription.plan_items.select_related("subject")
        return render(request, self.template_name, self.base_context(
            items=items, statuses=PlanItem.Status.choices,
            form=form or PlanItemForm(subscription=self.subscription),
            can_edit=self.role == "tutor" and self.subscription.is_current,
        ))

    def post(self, request, pk):
        if self.role != "tutor":
            raise PermissionDenied
        action = request.POST.get("action")
        try:
            services.require_current(self.subscription)
            if action == "add":
                form = PlanItemForm(request.POST, subscription=self.subscription)
                if not form.is_valid():
                    return self.get(request, pk, form=form)
                item = form.save(commit=False)
                item.subscription = self.subscription
                item.order = self.subscription.plan_items.filter(subject=item.subject).count() + 1
                item.save()
                messages.success(request, "Chapitre ajouté.")
            elif action == "import":
                count = services.import_reference_program(self.subscription)
                if count:
                    messages.success(request, f"{count} chapitre{'s' if count > 1 else ''} importé{'s' if count > 1 else ''} du programme.")
                else:
                    messages.info(request, "Aucun nouveau chapitre dans le programme de référence pour cette classe.")
            elif action == "status":
                item = get_object_or_404(PlanItem, pk=request.POST.get("item"), subscription=self.subscription)
                services.set_plan_item_status(item, request.POST.get("status"))
            elif action == "delete":
                item = get_object_or_404(PlanItem, pk=request.POST.get("item"), subscription=self.subscription)
                item.delete()
                messages.success(request, "Chapitre retiré du plan.")
        except PremiumError as error:
            messages.error(request, str(error))
        return redirect("premium:plan", pk=pk)


# ---------------------------------------------------------------------------
# Rapport mensuel
# ---------------------------------------------------------------------------
class MonthlyReportView(SubscriptionAccessMixin, TemplateView):
    template_name = "premium/report.html"

    def get_month(self):
        today = timezone.localdate()
        try:
            year, month = (int(part) for part in self.request.GET.get("mois", "").split("-"))
            return date(year, month, 1)
        except ValueError:
            return today.replace(day=1)

    def get_context_data(self, **kwargs):
        sub = self.subscription
        month = self.get_month()
        start, end = services.month_bounds(month.year, month.month)
        sessions = sub.sessions.filter(date__range=(start, end)).order_by("date").prefetch_related("plan_items__subject")
        grades = sub.grades.filter(date__range=(start, end)).select_related("subject")
        previous = (start - timedelta(days=1)).replace(day=1)
        following = end + timedelta(days=1)
        return super().get_context_data(**self.base_context(
            month=start,
            stats=services.attendance_stats(sub, start=max(start, sub.starts_on or start), end=end),
            sessions=sessions,
            grades=grades,
            acquired=sub.plan_items.filter(acquired_at__date__range=(start, end)).select_related("subject"),
            progress=services.progress_by_subject(sub),
            previous_month=previous.strftime("%Y-%m"),
            next_month=following.strftime("%Y-%m") if following <= timezone.localdate() else None,
        ), **kwargs)
