"""Variables disponibles dans tous les gabarits."""
from django.conf import settings


def site(request):
    return {
        "SITE_NAME": settings.SITE_NAME,
        "CONTACT_EMAIL": settings.CONTACT_EMAIL,
        "CONTACT_PHONE": settings.CONTACT_PHONE,
        "FEATURE_REVIEWS_ENABLED": settings.FEATURE_REVIEWS_ENABLED,
    }
