"""Tests des pages publiques par zone, du plan du site et des notifications."""
from django.test import TestCase
from django.urls import reverse

from core.testing import TempMediaTestCase, make_tutor, make_user
from locations.models import Commune
from notifications.models import Notification
from tutors.models import TutorProfile


class ZonePagesTests(TempMediaTestCase):
    def test_seeded_communes_exist(self):
        self.assertTrue(Commune.objects.filter(slug="cocody", city__slug="abidjan").exists())
        self.assertTrue(Commune.objects.filter(slug="bouake").exists())

    def test_zones_page_counts_only_verified_tutors(self):
        make_tutor(commune="cocody")
        make_tutor(commune="cocody", status=TutorProfile.Status.PENDING)
        response = self.client.get(reverse("locations:zones"))
        self.assertContains(response, "1 répétiteur vérifié")

    def test_commune_page(self):
        make_tutor(commune="yopougon")
        response = self.client.get(reverse("locations:commune", args=["yopougon"]))
        self.assertContains(response, "Répétiteur à domicile à Yopougon")
        self.assertContains(response, "Mathématiques")

    def test_unknown_commune_404(self):
        self.assertEqual(self.client.get(reverse("locations:commune", args=["inconnue"])).status_code, 404)


class SeoTests(TestCase):
    def test_sitemap_lists_communes(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/repetiteur-a-domicile/cocody/")

    def test_robots_hides_private_spaces(self):
        response = self.client.get("/robots.txt")
        self.assertContains(response, "Disallow: /gestion/")
        self.assertContains(response, "Sitemap: http://testserver/sitemap.xml")


class NotificationTests(TestCase):
    def test_open_marks_read_and_redirects(self):
        user = make_user()
        notification = Notification.objects.create(user=user, title="Test", url="/faq-inexistante/")
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse("core:home")), "notif-badge")
        response = self.client.get(reverse("notifications:open", args=[notification.pk]))
        self.assertRedirects(response, "/faq-inexistante/", fetch_redirect_response=False)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_external_url_is_not_followed(self):
        user = make_user()
        notification = Notification.objects.create(user=user, title="Test", url="https://pirate.example/")
        self.client.force_login(user)
        response = self.client.get(reverse("notifications:open", args=[notification.pk]))
        self.assertRedirects(response, reverse("notifications:list"))

    def test_cannot_open_someone_elses_notification(self):
        notification = Notification.objects.create(user=make_user(), title="Privé")
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(reverse("notifications:open", args=[notification.pk])).status_code, 404)
