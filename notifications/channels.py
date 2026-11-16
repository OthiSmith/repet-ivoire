"""
Canaux de notification.

Les canaux actifs sont listés dans settings.NOTIFICATION_CHANNELS.
Pour ajouter le SMS ou WhatsApp plus tard, créer une classe avec une
méthode `send(user, title, body, url)` et l'ajouter à ce réglage.
"""
from django.conf import settings
from django.core.mail import send_mail


class InAppChannel:
    """Notification visible dans l'espace de l'utilisateur (cloche)."""

    def send(self, user, title, body="", url=""):
        from .models import Notification

        Notification.objects.create(user=user, title=title, body=body, url=url)


class EmailChannel:
    """Copie de la notification par e-mail (à activer quand le SMTP est configuré)."""

    def send(self, user, title, body="", url=""):
        message = f"{body}\n\n{settings.SITE_URL}{url}" if url else body
        send_mail(f"{settings.SITE_NAME} : {title}", message, None, [user.email], fail_silently=True)
