"""
Suivi Premium d'un élève, rattaché à une mise en relation confirmée.

- Subscription : l'abonnement (demandé par le parent, activé par l'équipe après paiement).
- CurriculumUnit : programme de référence par classe et matière, géré par l'équipe.
- PlanItem : les chapitres prévus pour cet élève, avec leur état d'acquisition.
- Session : le cahier de séances tenu par le répétiteur et confirmé par le parent.
- Grade : les notes obtenues à l'école.
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Subscription(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Demandé"
        ACTIVE = "ACTIVE", "Actif"
        CANCELLED = "CANCELLED", "Annulé"

    class PaymentMethod(models.TextChoices):
        ORANGE = "ORANGE", "Orange Money"
        MTN = "MTN", "MTN MoMo"
        MOOV = "MOOV", "Moov Money"
        WAVE = "WAVE", "Wave"
        CASH = "CASH", "Espèces"
        OTHER = "OTHER", "Autre"

    request = models.OneToOneField("tutoring.TutoringRequest", on_delete=models.CASCADE, related_name="premium")
    status = models.CharField("statut", max_length=10, choices=Status.choices, default=Status.REQUESTED, db_index=True)
    months_requested = models.PositiveSmallIntegerField("durée souhaitée (mois)", default=1)
    starts_on = models.DateField("début", null=True, blank=True)
    ends_on = models.DateField("fin", null=True, blank=True)
    amount = models.PositiveIntegerField("montant payé (FCFA)", null=True, blank=True)
    payment_method = models.CharField("moyen de paiement", max_length=10, choices=PaymentMethod.choices, blank=True)
    payment_reference = models.CharField("référence du paiement", max_length=80, blank=True)
    requested_at = models.DateTimeField("demandé le", auto_now_add=True)
    activated_at = models.DateTimeField("activé le", null=True, blank=True)
    activated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="+")

    class Meta:
        verbose_name = "abonnement Premium"
        verbose_name_plural = "abonnements Premium"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Premium — {self.request}"

    @property
    def is_current(self):
        """Actif et dans sa période de validité : le suivi peut être alimenté."""
        today = timezone.localdate()
        return (self.status == self.Status.ACTIVE and self.starts_on is not None
                and self.starts_on <= today <= self.ends_on)

    @property
    def is_expired(self):
        return self.status == self.Status.ACTIVE and self.ends_on is not None and self.ends_on < timezone.localdate()

    @property
    def display_status(self):
        return "Expiré" if self.is_expired else self.get_status_display()

    @property
    def display_status_code(self):
        return "EXPIRED" if self.is_expired else self.status

    @property
    def tutor(self):
        proposal = self.request.chosen_proposal
        return proposal.tutor if proposal else None


class CurriculumUnit(models.Model):
    """Chapitre du programme de référence, proposé aux répétiteurs pour construire le plan d'un élève."""

    class Term(models.TextChoices):
        T1 = "T1", "1er trimestre"
        T2 = "T2", "2e trimestre"
        T3 = "T3", "3e trimestre"

    level = models.ForeignKey("catalog.Level", verbose_name="classe", on_delete=models.CASCADE, related_name="+")
    subject = models.ForeignKey("catalog.Subject", verbose_name="matière", on_delete=models.CASCADE, related_name="+")
    title = models.CharField("chapitre", max_length=160)
    term = models.CharField("période", max_length=2, choices=Term.choices, blank=True)
    order = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "chapitre du programme"
        verbose_name_plural = "programme de référence"
        ordering = ["level__order", "subject__order", "order"]

    def __str__(self):
        return f"{self.level} · {self.subject} · {self.title}"


class PlanItem(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Pas commencé"
        IN_PROGRESS = "IN_PROGRESS", "En cours"
        TO_REVIEW = "TO_REVIEW", "À revoir"
        ACQUIRED = "ACQUIRED", "Acquis"

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="plan_items")
    subject = models.ForeignKey("catalog.Subject", verbose_name="matière", on_delete=models.PROTECT, related_name="+")
    title = models.CharField("chapitre ou objectif", max_length=160)
    order = models.PositiveSmallIntegerField("ordre", default=0)
    status = models.CharField("état", max_length=12, choices=Status.choices, default=Status.NOT_STARTED)
    acquired_at = models.DateTimeField("acquis le", null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "chapitre suivi"
        verbose_name_plural = "chapitres suivis"
        ordering = ["subject__order", "order", "pk"]

    def __str__(self):
        return self.title


class Session(models.Model):
    class Status(models.TextChoices):
        DONE = "DONE", "Séance réalisée"
        CHILD_ABSENT = "CHILD_ABSENT", "Élève absent"
        CANCELLED = "CANCELLED", "Annulée (prévenu à l'avance)"
        TUTOR_ABSENT = "TUTOR_ABSENT", "Répétiteur absent"

    class ParentStatus(models.TextChoices):
        PENDING = "PENDING", "À confirmer"
        CONFIRMED = "CONFIRMED", "Confirmée"
        DISPUTED = "DISPUTED", "Problème signalé"

    class Issue(models.TextChoices):
        TUTOR_ABSENT = "TUTOR_ABSENT", "Le répétiteur n'est pas venu"
        LATE = "LATE", "Arrivé en retard"
        SHORTER = "SHORTER", "Séance écourtée"
        OTHER = "OTHER", "Autre problème"

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="sessions")
    date = models.DateField("date")
    duration_minutes = models.PositiveSmallIntegerField(
        "durée (minutes)", default=90, validators=[MinValueValidator(15), MaxValueValidator(300)])
    status = models.CharField("déroulement", max_length=12, choices=Status.choices, default=Status.DONE)
    plan_items = models.ManyToManyField(PlanItem, verbose_name="chapitres travaillés", blank=True,
                                        related_name="sessions")
    content = models.TextField("ce qui a été fait", blank=True)
    homework = models.TextField("devoirs donnés", blank=True)
    engagement = models.PositiveSmallIntegerField(
        "implication de l'élève (1 à 5)", null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)])
    tutor_comment = models.TextField("observations pour les parents", blank=True)
    declared_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    parent_status = models.CharField("confirmation du parent", max_length=10, choices=ParentStatus.choices,
                                     default=ParentStatus.PENDING)
    parent_issue = models.CharField("problème signalé", max_length=12, choices=Issue.choices, blank=True)
    parent_comment = models.TextField("commentaire du parent", blank=True)
    parent_responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "séance"
        verbose_name_plural = "séances"
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.date:%d/%m/%Y} — {self.get_status_display()}"

    @property
    def tutor_was_absent(self):
        return self.status == self.Status.TUTOR_ABSENT or self.parent_issue == self.Issue.TUTOR_ABSENT

    @property
    def awaits_parent(self):
        return self.status == self.Status.DONE and self.parent_status == self.ParentStatus.PENDING


class Grade(models.Model):
    class Kind(models.TextChoices):
        HOMEWORK = "HOMEWORK", "Devoir"
        QUIZ = "QUIZ", "Interrogation"
        EXAM = "EXAM", "Composition"
        MOCK = "MOCK", "Examen blanc"

    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="grades")
    subject = models.ForeignKey("catalog.Subject", verbose_name="matière", on_delete=models.PROTECT, related_name="+")
    date = models.DateField("date")
    kind = models.CharField("type", max_length=10, choices=Kind.choices, default=Kind.HOMEWORK)
    score = models.DecimalField("note", max_digits=5, decimal_places=2, validators=[MinValueValidator(0)])
    out_of = models.PositiveSmallIntegerField("sur", default=20, validators=[MinValueValidator(1)])
    comment = models.CharField("commentaire", max_length=255, blank=True)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "note"
        verbose_name_plural = "notes"
        ordering = ["date", "pk"]

    def __str__(self):
        return f"{self.subject} : {self.score}/{self.out_of}"

    @property
    def on_twenty(self):
        """Note ramenée sur 20, pour comparer les évaluations entre elles."""
        return (Decimal(self.score) * 20 / self.out_of).quantize(Decimal("0.01"))
