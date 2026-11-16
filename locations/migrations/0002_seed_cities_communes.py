"""Données de départ : les communes du District d'Abidjan et les principales villes."""
from django.db import migrations
from django.utils.text import slugify

ABIDJAN_COMMUNES = [
    "Abobo", "Adjamé", "Anyama", "Attécoubé", "Bingerville", "Cocody", "Koumassi",
    "Marcory", "Plateau", "Port-Bouët", "Songon", "Treichville", "Yopougon",
]

# Villes de l'intérieur : une commune du même nom, à détailler plus tard si besoin.
OTHER_CITIES = [
    "Yamoussoukro", "Bouaké", "San-Pédro", "Daloa", "Korhogo", "Man", "Gagnoa", "Grand-Bassam",
]


def seed(apps, schema_editor):
    City = apps.get_model("locations", "City")
    Commune = apps.get_model("locations", "Commune")
    abidjan, _ = City.objects.get_or_create(slug="abidjan", defaults={"name": "Abidjan", "order": 1})
    for name in ABIDJAN_COMMUNES:
        Commune.objects.get_or_create(slug=slugify(name), defaults={"city": abidjan, "name": name})
    for order, name in enumerate(OTHER_CITIES, start=2):
        city, _ = City.objects.get_or_create(slug=slugify(name), defaults={"name": name, "order": order})
        Commune.objects.get_or_create(slug=slugify(name), defaults={"city": city, "name": name})


class Migration(migrations.Migration):
    dependencies = [("locations", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
