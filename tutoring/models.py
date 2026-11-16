"""
Demandes des parents et propositions de répétiteurs.

Cycle de vie :
1. Le parent dépose une demande (NEW).
2. L'équipe propose jusqu'à MAX_PROPOSALS_PER_ROUND répétiteurs (SEARCHING).
3. Chaque répétiteur accepte ou refuse dans TUTOR_RESPONSE_DELAY_HOURS.
4. Le parent choisit parmi les propositions acceptées (MATCHED) :
   les coordonnées sont alors communiquées aux deux parties.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class TutoringRequest(models.Model):
    class Status(models.TextChoices):
        NEW = "NEW", "Nouvelle"
        SEARCHING = "SEARCHING", "Recherche en cours"
        MATCHED = "MATCHED", "Répétiteur trouvé"
        CANCELLED = "CANCELLED", "Annulée"
        CLOSED = "CLOSED", "Clôturée"

    OPEN_STATUSES = [Status.NEW, Status.SEARCHING]

    parent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tutoring_requests")
    child_first_name = models.CharField("prénom de l'enfant", max_length=80)
    level = models.ForeignKey("catalog.Level", verbose_name="classe", on_delete=models.PROTECT, related_name="+")
    subjects = models.ManyToManyField("catalog.Subject", verbose_name="matières", related_name="+")
    commune = models.ForeignKey("locations.Commune", verbose_name="commune", on_delete=models.PROTECT,
                                related_name="tutoring_requests")
    neighborhood = models.CharField("quartier", max_length=120)
    sessions_per_week = models.PositiveSmallIntegerField(
        "séances par semaine", choices=[(n, str(n)) for n in range(1, 6)], default=2)
    availability = models.TextField("disponibilités", help_text="Jours et heures où l'enfant est disponible.")
    goals = models.TextField("objectifs et difficultés", blank=True,
                             help_text="Ex. : « Préparer le BEPC, difficultés en géométrie »")
    budget_monthly = models.PositiveIntegerField("budget mensuel indicatif (FCFA)", null=True, blank=True)

    status = models.CharField("statut", max_length=10, choices=Status.choices, default=Status.NEW, db_index=True)
    admin_notes = models.TextField("notes internes", blank=True)
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    matched_at = models.DateTimeField("mise en relation le", null=True, blank=True)

    class Meta:
        verbose_name = "demande"
        verbose_name_plural = "demandes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.child_first_name} — {self.level} — {self.commune}"

    @property
    def is_open(self):
        return self.status in self.OPEN_STATUSES

    @property
    def chosen_proposal(self):
        return self.proposals.filter(status=Proposal.Status.CHOSEN).select_related("tutor__user").first()

    def active_proposals(self):
        return self.proposals.filter(status__in=Proposal.ACTIVE_STATUSES)


class ProposalQuerySet(models.QuerySet):
    def overdue(self):
        return self.filter(status=Proposal.Status.PENDING, expires_at__lt=timezone.now())


class Proposal(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente de réponse"
        ACCEPTED = "ACCEPTED", "Acceptée par le répétiteur"
        DECLINED = "DECLINED", "Refusée par le répétiteur"
        EXPIRED = "EXPIRED", "Expirée"
        CHOSEN = "CHOSEN", "Choisie par le parent"
        NOT_CHOSEN = "NOT_CHOSEN", "Non retenue"
        WITHDRAWN = "WITHDRAWN", "Retirée"

    ACTIVE_STATUSES = [Status.PENDING, Status.ACCEPTED]

    request = models.ForeignKey(TutoringRequest, on_delete=models.CASCADE, related_name="proposals")
    tutor = models.ForeignKey("tutors.TutorProfile", on_delete=models.CASCADE, related_name="proposals")
    status = models.CharField("statut", max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    tutor_message = models.TextField("message du répétiteur", blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField("proposée le", auto_now_add=True)
    expires_at = models.DateTimeField("réponse attendue avant")
    responded_at = models.DateTimeField("réponse le", null=True, blank=True)

    objects = ProposalQuerySet.as_manager()

    class Meta:
        verbose_name = "proposition"
        verbose_name_plural = "propositions"
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["request", "tutor"], name="unique_proposal_per_tutor")]

    def __str__(self):
        return f"{self.tutor} → {self.request}"

    @property
    def is_overdue(self):
        return self.status == self.Status.PENDING and self.expires_at < timezone.now()
