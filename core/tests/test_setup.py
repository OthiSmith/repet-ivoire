"""Tests de la phase 2 : le projet démarre et le socle est correctement configuré."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils.html import escape

from core.validators import normalize_ci_phone


class HomePageTests(TestCase):
    def test_home_page_renders(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/home.html")
        self.assertContains(response, "Le bon répétiteur pour faire réussir votre enfant.")
        # L'apostrophe du nom est échappée en HTML par les gabarits Django.
        self.assertContains(response, escape(settings.SITE_NAME))

    def test_unknown_page_returns_404(self):
        response = self.client.get("/page-qui-n-existe-pas/")
        self.assertEqual(response.status_code, 404)


class SettingsTests(SimpleTestCase):
    def test_locale_and_timezone(self):
        self.assertEqual(settings.LANGUAGE_CODE, "fr")
        self.assertEqual(settings.TIME_ZONE, "Africa/Abidjan")

    def test_custom_user_model(self):
        self.assertEqual(settings.AUTH_USER_MODEL, "accounts.User")

    def test_features_disabled_by_default(self):
        self.assertFalse(settings.FEATURE_PAYMENTS_ENABLED)
        self.assertFalse(settings.FEATURE_REVIEWS_ENABLED)

    def test_private_media_not_under_public_media(self):
        self.assertNotEqual(settings.PRIVATE_MEDIA_ROOT, settings.MEDIA_ROOT)
        self.assertFalse(str(settings.PRIVATE_MEDIA_ROOT).startswith(str(settings.MEDIA_ROOT)))


class PhoneValidatorTests(SimpleTestCase):
    def test_valid_formats_are_normalized(self):
        for raw in ["0701020304", "07 01 02 03 04", "+225 07 01 02 03 04", "00225-0501020304", "27.22.00.00.00"]:
            with self.subTest(raw=raw):
                self.assertRegex(normalize_ci_phone(raw), r"^\+225\d{10}$")

    def test_invalid_numbers_are_rejected(self):
        for raw in ["", "12345", "0901020304", "070102030", "07010203045", "abcdefghij"]:
            with self.subTest(raw=raw):
                with self.assertRaises(ValidationError):
                    normalize_ci_phone(raw)
