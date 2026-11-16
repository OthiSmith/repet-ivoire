"""Espace parent (demandes, choix du répétiteur) et réponses des répétiteurs aux propositions."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from accounts.permissions import ParentRequiredMixin, TutorRequiredMixin

from .forms import RespondForm, TutoringRequestForm
from .models import Proposal, TutoringRequest
from .services import ActionError, cancel_request, choose_proposal, create_request, respond_to_proposal


# ---------------------------------------------------------------------------
# Parents
# ---------------------------------------------------------------------------
class ParentDashboardView(ParentRequiredMixin, ListView):
    template_name = "tutoring/parent_dashboard.html"
    context_object_name = "requests"

    def get_queryset(self):
        return (self.request.user.tutoring_requests
                .select_related("level", "commune")
                .prefetch_related("subjects", "proposals"))


class RequestCreateView(ParentRequiredMixin, CreateView):
    form_class = TutoringRequestForm
    template_name = "tutoring/request_form.html"

    def form_valid(self, form):
        tutoring_request = create_request(form, self.request.user)
        messages.success(self.request, "Demande envoyée ! Notre équipe vous propose des répétiteurs très bientôt.")
        return redirect("tutoring:request_detail", pk=tutoring_request.pk)


class RequestDetailView(ParentRequiredMixin, DetailView):
    template_name = "tutoring/request_detail.html"
    context_object_name = "tutoring_request"

    def get_queryset(self):
        return self.request.user.tutoring_requests.select_related("level", "commune")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        proposals = self.object.proposals.select_related("tutor__user").prefetch_related(
            "tutor__subjects", "tutor__levels")
        context["accepted_proposals"] = proposals.filter(status=Proposal.Status.ACCEPTED)
        context["pending_count"] = proposals.filter(status=Proposal.Status.PENDING).count()
        context["chosen"] = proposals.filter(status=Proposal.Status.CHOSEN).first()
        return context


class RequestCancelView(ParentRequiredMixin, View):
    def post(self, request, pk):
        tutoring_request = get_object_or_404(TutoringRequest, pk=pk, parent=request.user)
        try:
            cancel_request(tutoring_request, request.user)
        except ActionError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Votre demande a été annulée.")
        return redirect("tutoring:request_detail", pk=pk)


class ProposalChooseView(ParentRequiredMixin, View):
    def post(self, request, pk):
        proposal = get_object_or_404(Proposal.objects.select_related("request"), pk=pk, request__parent=request.user)
        try:
            choose_proposal(proposal, request.user)
        except ActionError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f"C'est fait ! Vous pouvez maintenant contacter {proposal.tutor}.")
        return redirect("tutoring:request_detail", pk=proposal.request_id)


# ---------------------------------------------------------------------------
# Répétiteurs
# ---------------------------------------------------------------------------
class TutorProposalView(TutorRequiredMixin, View):
    template_name = "tutoring/tutor_proposal.html"

    def get_proposal(self, pk):
        return get_object_or_404(
            Proposal.objects.select_related("request__level", "request__commune", "request__parent", "tutor"),
            pk=pk, tutor__user=self.request.user,
        )

    def get(self, request, pk):
        proposal = self.get_proposal(pk)
        return render(request, self.template_name, {"proposal": proposal, "form": RespondForm()})

    def post(self, request, pk):
        proposal = self.get_proposal(pk)
        form = RespondForm(request.POST)
        accept = request.POST.get("decision") == "accept"
        message = form.cleaned_data["message"] if form.is_valid() else ""
        try:
            respond_to_proposal(proposal, request.user, accept, message)
        except ActionError as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Merci ! La famille va être informée." if accept else "Proposition refusée.")
        return redirect("tutoring:tutor_proposal", pk=pk)
