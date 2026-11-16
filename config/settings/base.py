"""
Paramètres communs à tous les environnements de Répét'Ivoire.

Les valeurs sensibles ou propres à chaque machine sont lues depuis le
fichier `.env` (non versionné) grâce à django-environ.
Voir `.env.example` pour la liste des variables disponibles.
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
)
environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Sécurité de base
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sitemaps",
    "django.forms",  # gabarits de widgets pour le rendu Bootstrap des formulaires
]

THIRD_PARTY_APPS = [
    "axes",  # protection contre les attaques par force brute sur la connexion
]

LOCAL_APPS = [
    "core",
    "accounts",
    "catalog",
    "locations",
    "tutors",
    "tutoring",
    "notifications",
    "reviews",
    "backoffice",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Doit rester en dernier : bloque les comptes après trop d'échecs.
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site",
                "notifications.context_processors.unread_notifications",
            ],
        },
    },
]

# Tous les formulaires sont rendus avec les gabarits Bootstrap de templates/forms/.
FORM_RENDERER = "core.forms.BootstrapFormRenderer"

# ---------------------------------------------------------------------------
# Base de données
# SQLite par défaut en local ; PostgreSQL via DATABASE_URL, par exemple :
# DATABASE_URL=postgres://utilisateur:motdepasse@localhost:5432/repetivoire
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "accounts.backends.EmailOrPhoneBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "/connexion/"
LOGIN_REDIRECT_URL = "/mon-espace/"
LOGOUT_REDIRECT_URL = "/"

# Sessions : expiration après 2 semaines, cookie inaccessible au JavaScript.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# django-axes : 5 échecs → blocage 30 minutes (par couple identifiant + IP).
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.5  # heures
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "accounts/lockout.html"

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Abidjan"
USE_I18N = True
USE_TZ = True
USE_THOUSAND_SEPARATOR = True

# ---------------------------------------------------------------------------
# Fichiers statiques et médias
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Médias publics (photos de profil redimensionnées).
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Médias privés (justificatifs) : JAMAIS servis directement.
# Accessibles uniquement via une vue réservée aux administrateurs.
PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Limites d'upload (validées aussi dans les formulaires).
MAX_UPLOAD_SIZE_MB = 5
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_PERMISSIONS = 0o640

# ---------------------------------------------------------------------------
# E-mail (console en local, SMTP en production)
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Répét'Ivoire <no-reply@repetivoire.local>")

# ---------------------------------------------------------------------------
# Paramètres métier de la plateforme
# ---------------------------------------------------------------------------
SITE_NAME = "Répét'Ivoire"
# Adresse publique du site, utilisée dans les e-mails (sans « / » final).
SITE_URL = env("SITE_URL", default="http://127.0.0.1:8000")
CONTACT_EMAIL = env("CONTACT_EMAIL", default="contact@repetivoire.local")
CONTACT_PHONE = env("CONTACT_PHONE", default="")
# Numéro WhatsApp affiché sur le site (bouton flottant). Vide = bouton masqué.
WHATSAPP_NUMBER = env("WHATSAPP_NUMBER", default="")

# Informations légales (mentions légales). À renseigner avant la mise en ligne.
LEGAL_COMPANY_NAME = env("LEGAL_COMPANY_NAME", default="")
LEGAL_COMPANY_FORM = env("LEGAL_COMPANY_FORM", default="")
LEGAL_RCCM = env("LEGAL_RCCM", default="")
LEGAL_ADDRESS = env("LEGAL_ADDRESS", default="")
LEGAL_DIRECTOR = env("LEGAL_DIRECTOR", default="")
LEGAL_HOST = env("LEGAL_HOST", default="")

# Interrupteurs de fonctionnalités (désactivées tant que l'équipe fondatrice
# n'en décide pas autrement).
FEATURE_REVIEWS_ENABLED = env.bool("FEATURE_REVIEWS_ENABLED", default=False)
FEATURE_PAYMENTS_ENABLED = env.bool("FEATURE_PAYMENTS_ENABLED", default=False)

# Délai de réponse accordé aux répétiteurs pour une proposition (heures).
TUTOR_RESPONSE_DELAY_HOURS = 48
# Nombre maximum de répétiteurs proposés par demande et par tour.
MAX_PROPOSALS_PER_ROUND = 3

# Canaux de notification actifs. Ajouter "notifications.channels.EmailChannel"
# une fois le SMTP configuré ; SMS et WhatsApp pourront suivre le même modèle.
NOTIFICATION_CHANNELS = env.list("NOTIFICATION_CHANNELS", default=["notifications.channels.InAppChannel"])

# ---------------------------------------------------------------------------
# Journalisation
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{asctime}] {levelname} {name} : {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
