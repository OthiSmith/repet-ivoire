"""Variables disponibles dans tous les gabarits."""
import re
from urllib.parse import quote

from django.conf import settings

WHATSAPP_DEFAULT_MESSAGE = "Bonjour, je cherche un répétiteur pour mon enfant."


def whatsapp_url(number, message=WHATSAPP_DEFAULT_MESSAGE):
    """Construit un lien wa.me à partir d'un numéro (ivoirien ou international)."""
    digits = re.sub(r"\D", "", number or "")
    if not digits:
        return ""
    if len(digits) == 10:  # numéro ivoirien saisi sans indicatif
        digits = f"225{digits}"
    return f"https://wa.me/{digits}?text={quote(message)}"


def site(request):
    return {
        "SITE_NAME": settings.SITE_NAME,
        "CONTACT_EMAIL": settings.CONTACT_EMAIL,
        "CONTACT_PHONE": settings.CONTACT_PHONE,
        "WHATSAPP_URL": whatsapp_url(settings.WHATSAPP_NUMBER),
        "FEATURE_REVIEWS_ENABLED": settings.FEATURE_REVIEWS_ENABLED,
    }
