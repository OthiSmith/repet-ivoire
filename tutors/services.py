"""Logique métier des profils répétiteurs : soumission et vérification."""
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from notifications.services import notify

from .models import TutorProfile


class ProfileError(Exception):
    """Action impossible sur le profil ; le message est affiché à l'utilisateur."""


def platform_admins():
    User = get_user_model()
    return User.objects.filter(Q(role=User.Role.ADMIN) | Q(is_staff=True), is_active=True)


def submit_profile(profile):
    if profile.status not in (TutorProfile.Status.DRAFT, TutorProfile.Status.REJECTED):
        raise ProfileError("Ce profil a déjà été soumis.")
    missing = profile.missing_items()
    if missing:
        raise ProfileError("Il manque encore : " + ", ".join(missing) + ".")
    profile.status = TutorProfile.Status.PENDING
    profile.submitted_at = timezone.now()
    profile.save(update_fields=["status", "submitted_at", "updated_at"])
    url = reverse("backoffice:tutor_review", args=[profile.pk])
    for admin in platform_admins():
        notify(admin, "Profil répétiteur à vérifier", f"{profile} a soumis son profil.", url)


def approve_profile(profile, admin):
    if profile.status != TutorProfile.Status.PENDING:
        raise ProfileError("Seul un profil en cours de vérification peut être validé.")
    profile.status = TutorProfile.Status.VERIFIED
    profile.verified_at = timezone.now()
    profile.verified_by = admin
    profile.rejection_reason = ""
    profile.save(update_fields=["status", "verified_at", "verified_by", "rejection_reason", "updated_at"])
    notify(profile.user, "Votre profil est vérifié !",
           "Félicitations : vous pouvez maintenant recevoir des propositions de cours.", reverse("tutors:dashboard"))


def reject_profile(profile, admin, reason):
    if profile.status != TutorProfile.Status.PENDING:
        raise ProfileError("Seul un profil en cours de vérification peut être renvoyé pour correction.")
    if not reason.strip():
        raise ProfileError("Indiquez les éléments à corriger.")
    profile.status = TutorProfile.Status.REJECTED
    profile.rejection_reason = reason.strip()
    profile.save(update_fields=["status", "rejection_reason", "updated_at"])
    notify(profile.user, "Votre profil est à compléter",
           f"Éléments à corriger : {profile.rejection_reason}", reverse("tutors:dashboard"))
