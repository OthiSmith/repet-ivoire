"""
Logique métier du suivi Premium.

Les vues appellent ces fonctions et affichent le message de PremiumError en cas de refus.
"""
import calendar
from datetime import date, timedelta

from django.db import transaction
from django.db.models import Avg, Q, Sum
from django.urls import reverse
from django.utils import timezone

from notifications.services import notify
from tutoring.models import TutoringRequest
from tutors.services import platform_admins

from .models import CurriculumUnit, PlanItem, Session, Subscription


class PremiumError(Exception):
    """Action refusée ; le message est affiché à l'utilisateur."""


def add_months(start, months):
    month_index = start.month - 1 + months
    year, month = start.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def _notify_admins(title, body, url):
    for admin in platform_admins():
        notify(admin, title, body, url)


def _tracking_url(subscription):
    return reverse("premium:tracking", args=[subscription.pk])


# ---------------------------------------------------------------------------
# Abonnement
# ---------------------------------------------------------------------------
def request_premium(tutoring_request, parent, months):
    if tutoring_request.parent_id != parent.pk:
        raise PremiumError("Cette demande ne vous appartient pas.")
    if tutoring_request.status != TutoringRequest.Status.MATCHED:
        raise PremiumError("Le suivi Premium est disponible une fois votre répétiteur choisi.")
    subscription, created = Subscription.objects.get_or_create(
        request=tutoring_request, defaults={"months_requested": months})
    if not created:
        if subscription.status == Subscription.Status.ACTIVE and not subscription.is_expired:
            raise PremiumError("Le suivi Premium est déjà actif pour cet enfant.")
        subscription.status = Subscription.Status.REQUESTED
        subscription.months_requested = months
        subscription.requested_at = timezone.now()
        subscription.save(update_fields=["status", "months_requested", "requested_at"])
    _notify_admins("Demande de suivi Premium", f"{tutoring_request} — {months} mois",
                   reverse("backoffice:premium_detail", args=[subscription.pk]))
    return subscription


@transaction.atomic
def activate(subscription, admin, months, amount=None, payment_method="", payment_reference=""):
    """Active ou prolonge l'abonnement de `months` mois après réception du paiement."""
    if months < 1:
        raise PremiumError("Durée invalide.")
    today = timezone.localdate()
    if subscription.status == Subscription.Status.ACTIVE and not subscription.is_expired:
        # Prolongation : la nouvelle période suit immédiatement la précédente.
        start_next = subscription.ends_on + timedelta(days=1)
    else:
        start_next = today
        subscription.starts_on = today
    subscription.ends_on = add_months(start_next, months) - timedelta(days=1)
    subscription.status = Subscription.Status.ACTIVE
    subscription.amount = amount
    subscription.payment_method = payment_method
    subscription.payment_reference = payment_reference
    subscription.activated_at = timezone.now()
    subscription.activated_by = admin
    subscription.save()
    body = f"Suivi actif jusqu'au {subscription.ends_on:%d/%m/%Y}."
    notify(subscription.request.parent, "Votre suivi Premium est actif", body, _tracking_url(subscription))
    tutor = subscription.tutor
    if tutor:
        notify(tutor.user, f"Suivi Premium activé pour {subscription.request.child_first_name}",
               "Établissez le plan de travail et renseignez le cahier de séances après chaque cours.",
               _tracking_url(subscription))


def cancel(subscription):
    if subscription.status == Subscription.Status.CANCELLED:
        raise PremiumError("Cet abonnement est déjà annulé.")
    subscription.status = Subscription.Status.CANCELLED
    subscription.save(update_fields=["status"])


def require_current(subscription):
    if not subscription.is_current:
        raise PremiumError("Le suivi Premium n'est pas actif : renouvelez-le pour ajouter de nouvelles informations.")


# ---------------------------------------------------------------------------
# Plan de travail
# ---------------------------------------------------------------------------
def import_reference_program(subscription):
    """Ajoute au plan les chapitres du programme de référence (classe et matières de la demande)."""
    require_current(subscription)
    req = subscription.request
    existing = set(subscription.plan_items.values_list("subject_id", "title"))
    units = CurriculumUnit.objects.filter(level=req.level, subject__in=req.subjects.all())
    created = [
        PlanItem(subscription=subscription, subject_id=u.subject_id, title=u.title, order=u.order)
        for u in units if (u.subject_id, u.title) not in existing
    ]
    PlanItem.objects.bulk_create(created)
    return len(created)


def set_plan_item_status(item, status):
    require_current(item.subscription)
    if status not in PlanItem.Status.values:
        raise PremiumError("État inconnu.")
    item.status = status
    item.acquired_at = timezone.now() if status == PlanItem.Status.ACQUIRED else None
    item.save(update_fields=["status", "acquired_at", "updated_at"])


# ---------------------------------------------------------------------------
# Cahier de séances et assiduité
# ---------------------------------------------------------------------------
def declare_session(form, subscription, tutor_user):
    require_current(subscription)
    session = form.save(commit=False)
    session.subscription = subscription
    session.declared_by = tutor_user
    if session.status != Session.Status.DONE:
        # Rien à confirmer pour une séance qui n'a pas eu lieu.
        session.parent_status = Session.ParentStatus.CONFIRMED
    session.save()
    form.save_m2m()
    child = subscription.request.child_first_name
    if session.status == Session.Status.DONE:
        notify(subscription.request.parent, f"Séance du {session.date:%d/%m} à confirmer",
               f"Le répétiteur a renseigné la séance de {child}. Confirmez qu'elle a bien eu lieu.",
               _tracking_url(subscription))
    else:
        notify(subscription.request.parent, f"Séance du {session.date:%d/%m} : {session.get_status_display()}",
               session.tutor_comment, _tracking_url(subscription))
    _check_repeated_absences(subscription)
    return session


def respond_to_session(session, parent, confirmed, issue="", comment=""):
    if session.subscription.request.parent_id != parent.pk:
        raise PremiumError("Cette séance ne vous concerne pas.")
    if not session.awaits_parent:
        raise PremiumError("Vous avez déjà répondu pour cette séance.")
    if not confirmed and issue not in Session.Issue.values:
        raise PremiumError("Précisez le problème rencontré.")
    session.parent_status = Session.ParentStatus.CONFIRMED if confirmed else Session.ParentStatus.DISPUTED
    session.parent_issue = "" if confirmed else issue
    session.parent_comment = comment.strip()
    session.parent_responded_at = timezone.now()
    session.save(update_fields=["parent_status", "parent_issue", "parent_comment", "parent_responded_at"])
    if not confirmed:
        _notify_admins("Problème signalé sur une séance",
                       f"{session.subscription.request} — {session.date:%d/%m} : {session.get_parent_issue_display()}",
                       reverse("backoffice:premium_detail", args=[session.subscription_id]))
        _check_repeated_absences(session.subscription)


def report_missed_session(subscription, parent, day, comment=""):
    """Le parent signale une séance prévue où le répétiteur n'est pas venu."""
    if subscription.request.parent_id != parent.pk:
        raise PremiumError("Ce suivi ne vous concerne pas.")
    if day > timezone.localdate():
        raise PremiumError("La date ne peut pas être dans le futur.")
    session = Session.objects.create(
        subscription=subscription, date=day, status=Session.Status.TUTOR_ABSENT, declared_by=parent,
        parent_status=Session.ParentStatus.DISPUTED, parent_issue=Session.Issue.TUTOR_ABSENT,
        parent_comment=comment.strip(), parent_responded_at=timezone.now(),
    )
    tutor = subscription.tutor
    if tutor:
        notify(tutor.user, "Absence signalée par la famille",
               f"La famille de {subscription.request.child_first_name} signale votre absence le {day:%d/%m}.",
               _tracking_url(subscription))
    _notify_admins("Absence du répétiteur signalée", f"{subscription.request} — {day:%d/%m}",
                   reverse("backoffice:premium_detail", args=[subscription.pk]))
    _check_repeated_absences(subscription)
    return session


ABSENCE_ALERT_THRESHOLD = 2
ABSENCE_ALERT_WINDOW_DAYS = 30


def _check_repeated_absences(subscription):
    since = timezone.localdate() - timedelta(days=ABSENCE_ALERT_WINDOW_DAYS)
    absences = subscription.sessions.filter(date__gte=since).filter(
        Q(status=Session.Status.TUTOR_ABSENT) | Q(parent_issue=Session.Issue.TUTOR_ABSENT)).count()
    if absences == ABSENCE_ALERT_THRESHOLD:  # une seule alerte quand le seuil est atteint
        _notify_admins("⚠ Absences répétées d'un répétiteur",
                       f"{subscription.tutor} : {absences} absences en {ABSENCE_ALERT_WINDOW_DAYS} jours "
                       f"({subscription.request}). Envisager un remplacement.",
                       reverse("backoffice:premium_detail", args=[subscription.pk]))


def request_replacement(subscription, parent, message):
    if subscription.request.parent_id != parent.pk:
        raise PremiumError("Ce suivi ne vous concerne pas.")
    require_current(subscription)
    if not message.strip():
        raise PremiumError("Expliquez-nous en quelques mots ce qui ne va pas.")
    _notify_admins("🔴 PRIORITAIRE — Demande de remplacement (Premium)",
                   f"{subscription.request} : {message.strip()}",
                   reverse("backoffice:premium_detail", args=[subscription.pk]))


# ---------------------------------------------------------------------------
# Indicateurs
# ---------------------------------------------------------------------------
def attendance_stats(subscription, start=None, end=None):
    """Assiduité sur une période (par défaut : depuis le début de l'abonnement jusqu'à aujourd'hui)."""
    today = timezone.localdate()
    start = start or subscription.starts_on or today
    end = min(end or today, subscription.ends_on or today, today)
    sessions = subscription.sessions.filter(date__gte=start, date__lte=end)
    held = sessions.filter(status=Session.Status.DONE).exclude(parent_issue=Session.Issue.TUTOR_ABSENT)
    weeks = max((end - start).days + 1, 0) / 7
    expected = round(weeks * subscription.request.sessions_per_week)
    held_count = held.count()
    minutes = held.aggregate(total=Sum("duration_minutes"))["total"] or 0
    return {
        "held": held_count,
        "confirmed": held.filter(parent_status=Session.ParentStatus.CONFIRMED).count(),
        "awaiting": held.filter(parent_status=Session.ParentStatus.PENDING).count(),
        "tutor_absences": sessions.filter(
            Q(status=Session.Status.TUTOR_ABSENT) | Q(parent_issue=Session.Issue.TUTOR_ABSENT)).count(),
        "late": sessions.filter(parent_issue=Session.Issue.LATE).count(),
        "shorter": sessions.filter(parent_issue=Session.Issue.SHORTER).count(),
        "child_absences": sessions.filter(status=Session.Status.CHILD_ABSENT).count(),
        "hours": round(minutes / 60, 1),
        "expected": expected,
        "rate": min(round(100 * held_count / expected), 100) if expected else None,
        "engagement": held.aggregate(avg=Avg("engagement"))["avg"],
    }


def progress_by_subject(subscription):
    """Avancement du plan par matière : nombre de chapitres dans chaque état et pourcentage acquis."""
    rows = {}
    for item in subscription.plan_items.select_related("subject"):
        row = rows.setdefault(item.subject, {"subject": item.subject, "total": 0, **{s: 0 for s in PlanItem.Status.values}})
        row["total"] += 1
        row[item.status] += 1
    result = []
    for row in rows.values():
        total = row["total"]
        row["percent"] = round(100 * row[PlanItem.Status.ACQUIRED] / total)
        # Largeurs des segments de la barre empilée (acquis, en cours, à revoir, pas commencé).
        row["segments"] = [
            {"status": s, "label": PlanItem.Status(s).label, "count": row[s], "width": 100 * row[s] / total}
            for s in [PlanItem.Status.ACQUIRED, PlanItem.Status.IN_PROGRESS, PlanItem.Status.TO_REVIEW,
                      PlanItem.Status.NOT_STARTED] if row[s]
        ]
        result.append(row)
    return result


def month_bounds(year, month):
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
