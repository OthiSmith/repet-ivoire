"""Tests du back-office : accès réservé et actions de l'équipe."""
from django.urls import reverse

from catalog.models import Level, Subject
from core.testing import TempMediaTestCase, make_admin, make_tutor, make_user
from locations.models import Commune
from tutoring.models import Proposal, TutoringRequest
from tutors.models import TutorProfile


class BackofficeTests(TempMediaTestCase):
    def setUp(self):
        self.admin = make_admin()
        self.tutor = make_tutor()
        self.request = TutoringRequest.objects.create(
            parent=make_user(), child_first_name="Yao", level=Level.objects.get(slug="3e"),
            commune=Commune.objects.get(slug="cocody"), neighborhood="Angré", availability="Soir",
        )
        self.request.subjects.add(Subject.objects.get(slug="mathematiques"))

    def test_pages_are_reserved_to_admins(self):
        urls = [
            reverse("backoffice:dashboard"), reverse("backoffice:tutor_list"),
            reverse("backoffice:tutor_review", args=[self.tutor.pk]),
            reverse("backoffice:request_list"), reverse("backoffice:request_detail", args=[self.request.pk]),
        ]
        for user in [make_user(), self.tutor.user]:
            self.client.force_login(user)
            for url in urls:
                with self.subTest(user=user.role, url=url):
                    self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.admin)
        for url in urls:
            with self.subTest(user="admin", url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_approves_profile(self):
        pending = make_tutor(status=TutorProfile.Status.PENDING)
        self.client.force_login(self.admin)
        self.client.post(reverse("backoffice:tutor_review", args=[pending.pk]), {"decision": "approve"})
        pending.refresh_from_db()
        self.assertEqual(pending.status, TutorProfile.Status.VERIFIED)

    def test_admin_rejects_profile_with_reason(self):
        pending = make_tutor(status=TutorProfile.Status.PENDING)
        self.client.force_login(self.admin)
        self.client.post(reverse("backoffice:tutor_review", args=[pending.pk]),
                         {"decision": "reject", "reason": "Photo floue"})
        pending.refresh_from_db()
        self.assertEqual(pending.status, TutorProfile.Status.REJECTED)
        self.assertEqual(pending.rejection_reason, "Photo floue")

    def test_request_page_suggests_and_proposes(self):
        self.client.force_login(self.admin)
        url = reverse("backoffice:request_detail", args=[self.request.pk])
        self.assertContains(self.client.get(url), str(self.tutor))
        self.client.post(url, {"action": "propose", "tutor": self.tutor.pk})
        self.assertTrue(Proposal.objects.filter(request=self.request, tutor=self.tutor).exists())

    def test_close_request(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("backoffice:request_detail", args=[self.request.pk]), {"action": "close"})
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, TutoringRequest.Status.CLOSED)
