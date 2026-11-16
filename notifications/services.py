"""Point d'entrée unique pour notifier un utilisateur sur tous les canaux actifs."""
import logging

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


def notify(user, title, body="", url=""):
    for path in settings.NOTIFICATION_CHANNELS:
        try:
            import_string(path)().send(user, title, body, url)
        except Exception:  # un canal en panne ne doit pas bloquer l'action en cours
            logger.exception("Échec du canal de notification %s", path)
