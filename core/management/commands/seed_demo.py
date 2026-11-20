"""
Crée des comptes et des données de démonstration pour explorer le site en local.

    python manage.py seed_demo

Refusé si DEBUG=False : ces comptes ont un mot de passe connu.
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from catalog.models import Level, Subject
from core.testing import image_file, pdf_file
from locations.models import Commune
from premium.models import CurriculumUnit, Grade, Session, Subscription
from premium.services import activate, import_reference_program, request_premium, set_plan_item_status
from tutoring.models import TutoringRequest
from tutoring.services import choose_proposal, propose_tutor, respond_to_proposal
from tutors.models import TutorDocument, TutorProfile

PASSWORD = "Demo!2026"

DEMO_PROGRAM = [
    ("Calcul littéral et identités remarquables", "T1"), ("Racines carrées", "T1"),
    ("Équations et inéquations du 1er degré", "T1"), ("Théorème de Thalès", "T2"),
    ("Trigonométrie dans le triangle rectangle", "T2"), ("Systèmes d'équations", "T2"),
    ("Statistiques", "T3"), ("Géométrie dans l'espace", "T3"),
]

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

        self.seed_premium(admin, parent)

        self.stdout.write(self.style.SUCCESS("Données de démonstration prêtes. Mot de passe commun : " + PASSWORD))
        for email in ["admin@demo.ci", "parent@demo.ci", "repetiteur1@demo.ci"]:
            self.stdout.write(f"  {email}")

    def seed_premium(self, admin, parent):
        """Un second enfant, déjà mis en relation avec Kouassi, avec un suivi Premium alimenté depuis 5 semaines."""
        if Subscription.objects.filter(request__parent=parent).exists():
            return
        maths = Subject.objects.get(slug="mathematiques")
        level = Level.objects.get(slug="3e")
        # Exemple de programme (à remplacer par le programme officiel validé par l'équipe).
        for order, (title, term) in enumerate(DEMO_PROGRAM, 1):
            CurriculumUnit.objects.get_or_create(level=level, subject=maths, title=title,
                                                 defaults={"order": order, "term": term})

        tutor = TutorProfile.objects.get(user__email="repetiteur1@demo.ci")
        demande = TutoringRequest.objects.create(
            parent=parent, child_first_name="Mariam", level=level, commune=Commune.objects.get(slug="cocody"),
            neighborhood="Angré 8e tranche", sessions_per_week=2, availability="Mardi et vendredi 17 h",
            goals="Réussir le BEPC en mathématiques.")
        demande.subjects.set([maths])
        proposal = propose_tutor(demande, tutor, admin)
        respond_to_proposal(proposal, tutor.user, accept=True, message="Ravi d'accompagner Mariam !")
        choose_proposal(proposal, parent)

        subscription = request_premium(demande, parent, 3)
        activate(subscription, admin, 3, amount=15000, payment_method="WAVE", payment_reference="DEMO-0001")
        today = timezone.localdate()
        subscription.starts_on = today - timedelta(days=35)
        subscription.save(update_fields=["starts_on"])
        import_reference_program(subscription)

        items = list(subscription.plan_items.order_by("order"))
        statuses = ["ACQUIRED", "ACQUIRED", "ACQUIRED", "IN_PROGRESS", "TO_REVIEW"]
        for item, status in zip(items, statuses):
            set_plan_item_status(item, status)

        sessions = [  # (jours avant aujourd'hui, chapitre, statut, confirmation parent, problème, implication)
            (33, 0, "DONE", "CONFIRMED", "", 3), (30, 0, "DONE", "CONFIRMED", "", 4),
            (26, 1, "DONE", "CONFIRMED", "", 4), (23, 1, "DONE", "DISPUTED", "LATE", 3),
            (19, 2, "DONE", "CONFIRMED", "", 4), (16, 2, "CHILD_ABSENT", "CONFIRMED", "", None),
            (12, 3, "DONE", "CONFIRMED", "", 5), (9, 4, "DONE", "CONFIRMED", "", 4),
            (5, 3, "DONE", "CONFIRMED", "", 4), (2, 4, "DONE", "PENDING", "", 5),
        ]
        for days, item_index, status, parent_status, issue, engagement in sessions:
            session = Session.objects.create(
                subscription=subscription, date=today - timedelta(days=days), status=status,
                content=f"Cours et exercices : {items[item_index].title}." if status == "DONE" else "",
                homework="Exercices 3 à 6 du manuel." if status == "DONE" else "",
                engagement=engagement, parent_status=parent_status, parent_issue=issue,
                tutor_comment="Mariam était malade, séance à rattraper." if status == "CHILD_ABSENT" else "",
                declared_by=tutor.user)
            if status == "DONE":
                session.plan_items.add(items[item_index])

        for days, score, kind in [(40, "8.5", "EXAM"), (28, "10", "HOMEWORK"), (14, "12.5", "QUIZ"), (3, "13", "HOMEWORK")]:
            Grade.objects.create(subscription=subscription, subject=maths, date=today - timedelta(days=days),
                                 score=score, kind=kind, added_by=parent)
