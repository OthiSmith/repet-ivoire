"""Profils des répétiteurs et justificatifs."""
import os
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models


class PrivateMediaStorage(FileSystemStorage):
    """Stockage des justificatifs dans PRIVATE_MEDIA_ROOT, jamais servi par une URL publique.

    Le dossier est relu dans les réglages à chaque accès (et non figé au chargement du modèle).
    """

    @property
    def base_location(self):
        return settings.PRIVATE_MEDIA_ROOT

    @property
    def location(self):
        return os.path.abspath(self.base_location)

    def url(self, name):
        raise ValueError("Les justificatifs n'ont pas d'URL publique : passer par la vue tutors:document_file.")


def private_storage():
    return PrivateMediaStorage()


def photo_upload_to(instance, filename):
    return f"tutors/photos/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


def document_upload_to(instance, filename):
    # Nom aléatoire : le nom d'origine (souvent « CNI_Nom_Prenom.pdf ») n'est pas conservé sur le disque.
    return f"tutors/documents/{instance.tutor_id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class TutorProfileQuerySet(models.QuerySet):
    def verified(self):
        return self.filter(status=TutorProfile.Status.VERIFIED, user__is_active=True, user__is_suspended=False)


class TutorProfile(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon"
        PENDING = "PENDING", "En cours de vérification"
        VERIFIED = "VERIFIED", "Vérifié"
        REJECTED = "REJECTED", "À corriger"

    class Education(models.TextChoices):
        BAC = "BAC", "BAC"
        BAC2 = "BAC2", "BAC + 2 (BTS, DUT, DEUG)"
        LICENCE = "LICENCE", "Licence"
        MASTER = "MASTER", "Master / Maîtrise"
        DOCTORATE = "DOCTORATE", "Doctorat"
        TEACHER = "TEACHER", "Diplôme d'enseignant (CAP, CAPES, ENS…)"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tutor_profile")
    photo = models.ImageField("photo", upload_to=photo_upload_to, blank=True,
                              help_text="Photo de face, visage bien visible. JPG ou PNG.")
    headline = models.CharField("titre du profil", max_length=120, blank=True,
                                help_text="Ex. : « Professeur de maths au lycée, 8 ans d'expérience »")
    bio = models.TextField("présentation", blank=True,
                           help_text="Votre parcours, votre méthode, ce qui vous motive.")
    education = models.CharField("diplôme le plus élevé", max_length=12, choices=Education.choices, blank=True)
    field_of_study = models.CharField("domaine d'études", max_length=120, blank=True)
    experience_years = models.PositiveSmallIntegerField("années d'expérience", default=0)
    subjects = models.ManyToManyField("catalog.Subject", verbose_name="matières enseignées", blank=True,
                                      related_name="tutors")
    levels = models.ManyToManyField("catalog.Level", verbose_name="niveaux enseignés", blank=True,
                                    related_name="tutors")
    communes = models.ManyToManyField("locations.Commune", verbose_name="communes où vous vous déplacez",
                                      blank=True, related_name="tutors")
    neighborhood = models.CharField("quartier de résidence", max_length=120, blank=True)
    availability = models.TextField("disponibilités", blank=True,
                                    help_text="Ex. : « Lundi, mercredi et vendredi après 17 h ; samedi matin »")
    hourly_rate = models.PositiveIntegerField("tarif horaire indicatif (FCFA)", null=True, blank=True)
    is_available = models.BooleanField("j'accepte de nouveaux élèves", default=True)

    status = models.CharField("statut", max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    rejection_reason = models.TextField("éléments à corriger", blank=True)
    submitted_at = models.DateTimeField("soumis le", null=True, blank=True)
    verified_at = models.DateTimeField("vérifié le", null=True, blank=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="vérifié par", null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TutorProfileQuerySet.as_manager()

    class Meta:
        verbose_name = "profil répétiteur"
        verbose_name_plural = "profils répétiteurs"
        ordering = ["-created_at"]

    def __str__(self):
        return self.user.get_full_name()

    @property
    def is_verified(self):
        return self.status == self.Status.VERIFIED

    @property
    def can_be_edited(self):
        return self.status != self.Status.PENDING

    def has_document(self, kind):
        return self.documents.filter(kind=kind).exists()

    def missing_items(self):
        """Liste des éléments à compléter avant de pouvoir soumettre le profil."""
        missing = []
        if not self.photo:
            missing.append("une photo")
        if not self.headline or len(self.bio) < 80:
            missing.append("un titre et une présentation (80 caractères minimum)")
        if not self.education:
            missing.append("votre diplôme le plus élevé")
        if not self.subjects.exists():
            missing.append("au moins une matière")
        if not self.levels.exists():
            missing.append("au moins un niveau")
        if not self.communes.exists():
            missing.append("au moins une commune")
        if not self.availability:
            missing.append("vos disponibilités")
        if not self.has_document(TutorDocument.Kind.ID_CARD):
            missing.append("votre pièce d'identité")
        if not self.has_document(TutorDocument.Kind.DIPLOMA):
            missing.append("votre diplôme")
        return missing


class TutorDocument(models.Model):
    class Kind(models.TextChoices):
        ID_CARD = "ID_CARD", "Pièce d'identité (CNI, passeport, attestation)"
        DIPLOMA = "DIPLOMA", "Diplôme le plus élevé"
        OTHER = "OTHER", "Autre justificatif (attestation, certificat…)"

    tutor = models.ForeignKey(TutorProfile, on_delete=models.CASCADE, related_name="documents")
    kind = models.CharField("type de document", max_length=10, choices=Kind.choices)
    file = models.FileField("fichier", upload_to=document_upload_to, storage=private_storage)
    original_name = models.CharField("nom d'origine", max_length=255, blank=True)
    uploaded_at = models.DateTimeField("ajouté le", auto_now_add=True)

    class Meta:
        verbose_name = "justificatif"
        verbose_name_plural = "justificatifs"
        ordering = ["kind", "-uploaded_at"]

    def __str__(self):
        return f"{self.get_kind_display()} — {self.tutor}"
