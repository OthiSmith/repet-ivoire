"""Référentiel pédagogique : niveaux scolaires et matières."""
from django.db import models


class Level(models.Model):
    """Classe du système scolaire ivoirien (CP1 → Terminale)."""

    class Cycle(models.TextChoices):
        PRIMARY = "PRIMARY", "Primaire"
        MIDDLE = "MIDDLE", "Collège"
        HIGH = "HIGH", "Lycée"

    name = models.CharField("nom", max_length=40, unique=True)
    slug = models.SlugField(unique=True)
    cycle = models.CharField("cycle", max_length=10, choices=Cycle.choices)
    exam = models.CharField("examen de fin de cycle", max_length=20, blank=True,
                            help_text="CEPE, BEPC ou BAC si la classe y prépare.")
    order = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "niveau"
        verbose_name_plural = "niveaux"
        ordering = ["order"]

    def __str__(self):
        return self.name


class Subject(models.Model):
    name = models.CharField("nom", max_length=60, unique=True)
    slug = models.SlugField(unique=True)
    order = models.PositiveSmallIntegerField("ordre", default=0)
    is_active = models.BooleanField("active", default=True)

    class Meta:
        verbose_name = "matière"
        verbose_name_plural = "matières"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name
