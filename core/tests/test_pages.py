"""Tests des pages publiques : FAQ, pages légales, WhatsApp, aperçus de partage."""
from django.test import TestCase, override_settings
from django.urls import reverse

from core.context_processors import whatsapp_url


class PublicPagesTests(TestCase):
    def test_public_pages_render(self):
        for name in ["core:faq", "core:legal_notice", "core:privacy", "core:terms"]:
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)

    def test_footer_links_to_legal_pages(self):
        response = self.client.get(reverse("core:home"))
        for name in ["core:legal_notice", "core:privacy", "core:terms", "core:faq"]:
            self.assertContains(response, reverse(name))

    def test_home_has_open_graph_tags(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, 'property="og:title"')
        self.assertContains(response, "og-image.png")

    @override_settings(LEGAL_RCCM="CI-ABJ-2026-B-00001")
    def test_legal_notice_uses_settings(self):
        response = self.client.get(reverse("core:legal_notice"))
        self.assertContains(response, "CI-ABJ-2026-B-00001")


class WhatsappTests(TestCase):
    def test_url_adds_ivorian_prefix(self):
        self.assertTrue(whatsapp_url("07 01 02 03 04").startswith("https://wa.me/2250701020304?text="))

    def test_url_keeps_international_number(self):
        self.assertTrue(whatsapp_url("+225 07 01 02 03 04").startswith("https://wa.me/2250701020304?"))

    def test_empty_number_gives_no_url(self):
        self.assertEqual(whatsapp_url(""), "")

    @override_settings(WHATSAPP_NUMBER="")
    def test_button_hidden_without_number(self):
        response = self.client.get(reverse("core:home"))
        self.assertNotContains(response, "whatsapp-float")

    @override_settings(WHATSAPP_NUMBER="0701020304")
    def test_button_shown_with_number(self):
        response = self.client.get(reverse("core:home"))
        self.assertContains(response, "whatsapp-float")
        self.assertContains(response, "https://wa.me/2250701020304")
