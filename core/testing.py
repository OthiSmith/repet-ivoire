"""Fabriques d'objets pour les tests (sans dépendance externe)."""
import io
import itertools
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from accounts.models import User
from catalog.models import Level, Subject
from locations.models import Commune
from tutors.models import TutorDocument, TutorProfile

_counter = itertools.count(1)
PASSWORD = "MotDePasse!2026"


class TempMediaTestCase(TestCase):
    """Écrit les fichiers téléversés dans des dossiers temporaires, supprimés après les tests."""

    @classmethod
    def setUpClass(cls):
        cls.media_root = tempfile.mkdtemp()
        cls.private_media_root = tempfile.mkdtemp()
        cls._media_override = override_settings(MEDIA_ROOT=cls.media_root, PRIVATE_MEDIA_ROOT=cls.private_media_root)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        shutil.rmtree(cls.private_media_root, ignore_errors=True)


def make_user(role=User.Role.PARENT, **extra):
    n = next(_counter)
    defaults = {
        "email": f"user{n}@exemple.ci",
        "phone": f"07{n:08d}",
        "first_name": f"Prénom{n}",
        "last_name": f"Nom{n}",
        "role": role,
    }
    defaults.update(extra)
    return User.objects.create_user(password=PASSWORD, **defaults)


def make_admin():
    return make_user(role=User.Role.ADMIN, is_staff=True)


def image_file(name="photo.png", size=(800, 600)):
    buffer = io.BytesIO()
    Image.new("RGB", size, "#1D5FD1").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def pdf_file(name="diplome.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 test", content_type="application/pdf")


def make_tutor(status=TutorProfile.Status.VERIFIED, level="3e", commune="cocody", subjects=("mathematiques",)):
    """Répétiteur au profil complet, avec ses justificatifs."""
    user = make_user(role=User.Role.TUTOR)
    profile = TutorProfile.objects.create(
        user=user, photo=image_file(), headline="Professeur de mathématiques",
        bio="Enseignant passionné, j'accompagne les collégiens et lycéens depuis plusieurs années avec méthode.",
        education=TutorProfile.Education.MASTER, experience_years=5,
        availability="Lundi et mercredi après 17 h", status=status,
    )
    profile.levels.add(Level.objects.get(slug=level))
    profile.communes.add(Commune.objects.get(slug=commune))
    profile.subjects.add(*Subject.objects.filter(slug__in=subjects))
    for kind in (TutorDocument.Kind.ID_CARD, TutorDocument.Kind.DIPLOMA):
        TutorDocument.objects.create(tutor=profile, kind=kind, file=pdf_file(), original_name="doc.pdf")
    return profile
