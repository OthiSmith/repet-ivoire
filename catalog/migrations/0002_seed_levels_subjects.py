"""Données de départ : classes du système ivoirien et matières courantes."""
from django.db import migrations
from django.utils.text import slugify

LEVELS = [
    ("CP1", "PRIMARY", ""), ("CP2", "PRIMARY", ""), ("CE1", "PRIMARY", ""), ("CE2", "PRIMARY", ""),
    ("CM1", "PRIMARY", ""), ("CM2", "PRIMARY", "CEPE"),
    ("6e", "MIDDLE", ""), ("5e", "MIDDLE", ""), ("4e", "MIDDLE", ""), ("3e", "MIDDLE", "BEPC"),
    ("2nde", "HIGH", ""), ("1re", "HIGH", ""), ("Terminale", "HIGH", "BAC"),
]

SUBJECTS = [
    "Mathématiques", "Français", "Anglais", "Physique-Chimie", "SVT", "Histoire-Géographie",
    "Philosophie", "Espagnol", "Allemand", "EDHC", "Informatique", "Méthodologie et aide aux devoirs",
]


def seed(apps, schema_editor):
    Level = apps.get_model("catalog", "Level")
    Subject = apps.get_model("catalog", "Subject")
    for order, (name, cycle, exam) in enumerate(LEVELS, start=1):
        Level.objects.get_or_create(slug=slugify(name), defaults={"name": name, "cycle": cycle, "exam": exam, "order": order})
    for order, name in enumerate(SUBJECTS, start=1):
        Subject.objects.get_or_create(slug=slugify(name), defaults={"name": name, "order": order})


class Migration(migrations.Migration):
    dependencies = [("catalog", "0001_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
