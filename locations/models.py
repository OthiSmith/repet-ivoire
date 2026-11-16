"""
Zones d'intervention : Ville → Commune.

Le quartier est saisi librement par les familles et les répétiteurs :
une liste fermée de quartiers serait vite incomplète.
"""
from django.db import models
from django.urls import reverse


class City(models.Model):
    name = models.CharField("nom", max_length=80, unique=True)
    slug = models.SlugField(unique=True)
    order = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        verbose_name = "ville"
        verbose_name_plural = "villes"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Commune(models.Model):
    city = models.ForeignKey(City, verbose_name="ville", on_delete=models.PROTECT, related_name="communes")
    name = models.CharField("nom", max_length=80)
    slug = models.SlugField(unique=True, help_text="Utilisé dans l'adresse de la page publique de la commune.")
    is_active = models.BooleanField("active", default=True)

    class Meta:
        verbose_name = "commune"
        verbose_name_plural = "communes"
        ordering = ["city__order", "city__name", "name"]
        constraints = [models.UniqueConstraint(fields=["city", "name"], name="unique_commune_per_city")]

    def __str__(self):
        if self.name == self.city.name:
            return self.name
        return f"{self.name} ({self.city.name})"

    def get_absolute_url(self):
        return reverse("locations:commune", kwargs={"slug": self.slug})
