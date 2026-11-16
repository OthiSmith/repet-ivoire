"""
Expire les propositions restées sans réponse.

À planifier toutes les heures en production (cron, tâche planifiée…) :
    python manage.py expire_proposals
"""
from django.core.management.base import BaseCommand

from tutoring.services import expire_overdue_proposals


class Command(BaseCommand):
    help = "Passe en « expirée » les propositions sans réponse après le délai prévu."

    def handle(self, *args, **options):
        count = expire_overdue_proposals()
        self.stdout.write(self.style.SUCCESS(f"{count} proposition(s) expirée(s)."))
