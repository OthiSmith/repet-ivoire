"""
Crée des comptes et des données de démonstration pour explorer le site en local.

    python manage.py seed_demo

Refusé si DEBUG=False : ces comptes ont un mot de passe connu.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from catalog.models import Level, Subject
from core.testing import image_file, pdf_file
from locations.models import Commune
from tutoring.models import TutoringRequest
from tutors.models import TutorDocument, TutorProfile

PASSWORD = "Demo!2026"

TUTORS = [
    ("Kouassi", "Bamba", "0700000001", "Professeur de mathématiques au lycée", "MASTER", 8,
     ["mathematiques", "physique-chimie"], ["3e", "2nde", "1re", "terminale"], ["cocody", "bingerville"], "VERIFIED"),
    ("Aminata", "Diallo", "0500000002", "Étudiante en lettres modernes, patiente et méthodique", "LICENCE", 3,
     ["francais", "anglais", "methodologie-et-aide-aux-devoirs"], ["cm1", "cm2", "6e", "5e"], ["yopougon", "attecoube"], "VERIFIED"),
    ("Jean-Marc", "Yao", "0100000003", "Ingénieur, prépare au BAC scientifique", "MASTER", 5,
     ["mathematiques", "physique-chimie", "svt"], ["1re", "terminale"], ["cocody", "marcory", "plateau"], "VERIFIED"),
    ("Fatou", "Koné", "0700000004", "Institutrice, spécialiste du primaire", "TEACHER", 12,
     ["francais", "mathematiques"], ["cp1", "cp2", "ce1", "ce2", "cm1", "cm2"], ["abobo", "adjame"], "PENDING"),
]


class Command(BaseCommand):
    help = "Crée des comptes de démonstration (administrateur, parent, répétiteurs) et une demande."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Commande réservée au développement (DEBUG=True).")

        def user(email, phone, first, last, role, **extra):
            account, created = User.objects.get_or_create(
                email=email, defaults={"phone": f"+225{phone}", "first_name": first, "last_name": last,
                                       "role": role, **extra})
            if created:
                account.set_password(PASSWORD)
                account.save()
            return account

        admin = user("admin@demo.ci", "2700000000", "Équipe", "Répét'Ivoire", User.Role.ADMIN, is_staff=True)
        parent = user("parent@demo.ci", "0700000100", "Awa", "Traoré", User.Role.PARENT)

        for i, (first, last, phone, headline, education, years, subjects, levels, communes, status) in enumerate(TUTORS, 1):
            account = user(f"repetiteur{i}@demo.ci", phone, first, last, User.Role.TUTOR)
            profile, created = TutorProfile.objects.get_or_create(user=account)
            if not created:
                continue
            profile.photo = image_file(f"demo{i}.png", size=(300, 300))
            profile.headline = headline
            profile.bio = (f"Je m'appelle {first}. {headline}. J'accompagne chaque élève avec bienveillance, "
                           "en partant de ses difficultés et en fixant des objectifs clairs avec la famille.")
            profile.education = education
            profile.experience_years = years
            profile.availability = "En semaine après 17 h, samedi matin"
            profile.hourly_rate = 3000 + 500 * years
            profile.status = status
            profile.save()
            profile.subjects.set(Subject.objects.filter(slug__in=subjects))
            profile.levels.set(Level.objects.filter(slug__in=levels))
            profile.communes.set(Commune.objects.filter(slug__in=communes))
            for kind in (TutorDocument.Kind.ID_CARD, TutorDocument.Kind.DIPLOMA):
                TutorDocument.objects.create(tutor=profile, kind=kind, file=pdf_file(), original_name="exemple.pdf")

        if not parent.tutoring_requests.exists():
            demande = TutoringRequest.objects.create(
                parent=parent, child_first_name="Yannick", level=Level.objects.get(slug="3e"),
                commune=Commune.objects.get(slug="cocody"), neighborhood="Riviera 2", sessions_per_week=2,
                availability="Mardi et jeudi de 17 h à 19 h", goals="Préparer le BEPC, difficultés en géométrie.",
                budget_monthly=40000)
            demande.subjects.set(Subject.objects.filter(slug="mathematiques"))

        self.stdout.write(self.style.SUCCESS("Données de démonstration prêtes. Mot de passe commun : " + PASSWORD))
        for email in ["admin@demo.ci", "parent@demo.ci", "repetiteur1@demo.ci"]:
            self.stdout.write(f"  {email}")
