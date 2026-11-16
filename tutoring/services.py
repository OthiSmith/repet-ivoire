"""
Logique métier de la mise en relation.

Toutes les transitions d'état passent par ces fonctions : les vues se
contentent de les appeler et d'afficher le message d'ActionError en cas de refus.
"""
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from notifications.services import notify
from tutors.models import TutorProfile
from tutors.services import platform_admins

from .models import Proposal, TutoringRequest


class ActionError(Exception):
    """Action refusée ; le message est affiché à l'utilisateur."""


def _notify_admins(title, body, url):
    for admin in platform_admins():
        notify(admin, title, body, url)


def create_request(form, parent):
    tutoring_request = form.save(commit=False)
    tutoring_request.parent = parent
    tutoring_request.save()
    form.save_m2m()
    _notify_admins("Nouvelle demande de répétiteur", str(tutoring_request),
                   reverse("backoffice:request_detail", args=[tutoring_request.pk]))
    return tutoring_request


def suggest_tutors(tutoring_request):
    """Répétiteurs vérifiés et disponibles : même niveau, même commune, au moins une matière en commun."""
    subject_ids = list(tutoring_request.subjects.values_list("pk", flat=True))
    return (
        TutorProfile.objects.verified()
        .filter(is_available=True, levels=tutoring_request.level, communes=tutoring_request.commune)
        .exclude(proposals__request=tutoring_request)
        .annotate(matching_subjects=Count("subjects", filter=Q(subjects__in=subject_ids), distinct=True))
        .filter(matching_subjects__gt=0)
        .select_related("user")
        .order_by("-matching_subjects", "-experience_years")
    )


@transaction.atomic
def propose_tutor(tutoring_request, tutor, admin):
    if not tutoring_request.is_open:
        raise ActionError("Cette demande n'est plus ouverte.")
    if not tutor.is_verified or not tutor.is_available:
        raise ActionError("Ce répétiteur n'est pas vérifié ou n'accepte pas de nouveaux élèves.")
    if tutoring_request.proposals.filter(tutor=tutor).exists():
        raise ActionError("Ce répétiteur a déjà été proposé pour cette demande.")
    if tutoring_request.active_proposals().count() >= settings.MAX_PROPOSALS_PER_ROUND:
        raise ActionError(f"Maximum {settings.MAX_PROPOSALS_PER_ROUND} propositions en cours par demande.")
    proposal = Proposal.objects.create(
        request=tutoring_request, tutor=tutor, created_by=admin,
        expires_at=timezone.now() + timedelta(hours=settings.TUTOR_RESPONSE_DELAY_HOURS),
    )
    if tutoring_request.status == TutoringRequest.Status.NEW:
        tutoring_request.status = TutoringRequest.Status.SEARCHING
        tutoring_request.save(update_fields=["status", "updated_at"])
    notify(tutor.user, "Nouvelle proposition de cours",
           f"{tutoring_request.level} — {tutoring_request.commune}. "
           f"Répondez avant {settings.TUTOR_RESPONSE_DELAY_HOURS} h.",
           reverse("tutoring:tutor_proposal", args=[proposal.pk]))
    return proposal


@transaction.atomic
def respond_to_proposal(proposal, tutor_user, accept, message=""):
    if proposal.tutor.user_id != tutor_user.pk:
        raise ActionError("Cette proposition ne vous est pas destinée.")
    if proposal.is_overdue:
        raise ActionError("Le délai de réponse est dépassé.")
    if proposal.status != Proposal.Status.PENDING:
        raise ActionError("Vous avez déjà répondu à cette proposition.")
    if not proposal.request.is_open:
        raise ActionError("Cette demande n'est plus ouverte.")
    proposal.status = Proposal.Status.ACCEPTED if accept else Proposal.Status.DECLINED
    proposal.tutor_message = message.strip()
    proposal.responded_at = timezone.now()
    proposal.save(update_fields=["status", "tutor_message", "responded_at"])
    detail_url = reverse("backoffice:request_detail", args=[proposal.request_id])
    if accept:
        notify(proposal.request.parent, "Un répétiteur est disponible pour votre enfant",
               f"{proposal.tutor} a accepté votre demande. Consultez son profil.",
               reverse("tutoring:request_detail", args=[proposal.request_id]))
    else:
        _notify_admins("Proposition refusée", f"{proposal.tutor} a refusé : {proposal.request}.", detail_url)


@transaction.atomic
def choose_proposal(proposal, parent_user):
    tutoring_request = proposal.request
    if tutoring_request.parent_id != parent_user.pk:
        raise ActionError("Cette demande ne vous appartient pas.")
    if not tutoring_request.is_open:
        raise ActionError("Cette demande n'est plus ouverte.")
    if proposal.status != Proposal.Status.ACCEPTED:
        raise ActionError("Ce répétiteur n'a pas (encore) accepté la demande.")
    now = timezone.now()
    proposal.status = Proposal.Status.CHOSEN
    proposal.save(update_fields=["status"])
    for other in tutoring_request.active_proposals().exclude(pk=proposal.pk).select_related("tutor__user"):
        other.status = Proposal.Status.NOT_CHOSEN
        other.save(update_fields=["status"])
        notify(other.tutor.user, "Proposition non retenue",
               f"La famille a choisi un autre répétiteur ({tutoring_request.level} — {tutoring_request.commune}).",
               reverse("tutors:dashboard"))
    tutoring_request.status = TutoringRequest.Status.MATCHED
    tutoring_request.matched_at = now
    tutoring_request.save(update_fields=["status", "matched_at", "updated_at"])
    notify(proposal.tutor.user, "Vous avez été choisi !",
           "La famille vous a choisi. Ses coordonnées sont maintenant visibles : contactez-la pour organiser le premier cours.",
           reverse("tutoring:tutor_proposal", args=[proposal.pk]))
    _notify_admins("Mise en relation confirmée", f"{tutoring_request} ↔ {proposal.tutor}",
                   reverse("backoffice:request_detail", args=[tutoring_request.pk]))


@transaction.atomic
def cancel_request(tutoring_request, parent_user):
    if tutoring_request.parent_id != parent_user.pk:
        raise ActionError("Cette demande ne vous appartient pas.")
    if not tutoring_request.is_open:
        raise ActionError("Cette demande ne peut plus être annulée.")
    for proposal in tutoring_request.active_proposals().select_related("tutor__user"):
        proposal.status = Proposal.Status.WITHDRAWN
        proposal.save(update_fields=["status"])
        notify(proposal.tutor.user, "Demande annulée",
               f"La famille a annulé sa demande ({tutoring_request.level} — {tutoring_request.commune}).",
               reverse("tutors:dashboard"))
    tutoring_request.status = TutoringRequest.Status.CANCELLED
    tutoring_request.save(update_fields=["status", "updated_at"])


@transaction.atomic
def withdraw_proposal(proposal):
    if proposal.status not in Proposal.ACTIVE_STATUSES:
        raise ActionError("Cette proposition n'est plus active.")
    proposal.status = Proposal.Status.WITHDRAWN
    proposal.save(update_fields=["status"])
    notify(proposal.tutor.user, "Proposition retirée",
           f"La proposition ({proposal.request.level} — {proposal.request.commune}) a été retirée par l'équipe.",
           reverse("tutors:dashboard"))


def close_request(tutoring_request):
    if tutoring_request.status in (TutoringRequest.Status.CANCELLED, TutoringRequest.Status.CLOSED):
        raise ActionError("Cette demande est déjà fermée.")
    for proposal in tutoring_request.active_proposals():
        withdraw_proposal(proposal)
    tutoring_request.status = TutoringRequest.Status.CLOSED
    tutoring_request.save(update_fields=["status", "updated_at"])


def expire_overdue_proposals():
    """Passe en EXPIRED les propositions sans réponse dans le délai. Renvoie leur nombre."""
    overdue = list(Proposal.objects.overdue().select_related("request", "tutor"))
    for proposal in overdue:
        proposal.status = Proposal.Status.EXPIRED
        proposal.save(update_fields=["status"])
        _notify_admins("Proposition expirée", f"{proposal.tutor} n'a pas répondu : {proposal.request}.",
                       reverse("backoffice:request_detail", args=[proposal.request_id]))
    return len(overdue)
