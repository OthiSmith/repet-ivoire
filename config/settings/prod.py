"""
Paramètres de production.

Utilisés en définissant DJANGO_SETTINGS_MODULE=config.settings.prod.
Prérequis : HTTPS actif, PostgreSQL configuré via DATABASE_URL,
`python manage.py collectstatic` exécuté.
"""
from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

LOGGING["root"]["level"] = "WARNING"  # noqa: F405
