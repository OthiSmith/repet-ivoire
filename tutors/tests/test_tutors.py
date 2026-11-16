"""Tests de l'espace répétiteur et de la vérification des profils."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from accounts.models import User
from catalog.models import Level, Subject
from core.testing import TempMediaTestCase, image_file, make_admin, make_tutor, make_user, pdf_file
from locations.models import Commune
from notifications.models import Notification
from tutors.models import TutorDocument, TutorProfile
from tutors.services import ProfileError, approve_profile, reject_profile, submit_profile


class ProfileFlowTests(TempMediaTestCase):
    def setUp(self):
        self.user = make_user(role=User.Role.TUTOR)
        self.client.force_login(self.user)

    def test_dashboard_creates_draft_profile(self):
        response = self.client.get(reverse("tutors:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.tutor_profile.status, TutorProfile.Status.DRAFT)
        self.assertContains(response, "Il manque encore")

    def test_parent_cannot_access_tutor_space(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(reverse("tutors:dashboard")).status_code, 403)

    def test_edit_profile_resizes_photo(self):
        self.client.get(reverse("tutors:dashboard"))
        response = self.client.post(reverse("tutors:profile_edit"), {
            "photo": image_file(size=(2000, 1500)), "headline": "Prof de maths", "bio": "x" * 100,
            "education": "MASTER", "experience_years": 3,
            "subjects": [Subject.objects.get(slug="mathematiques").pk],
            "levels": [Level.objects.get(slug="3e").pk],
            "communes": [Commune.objects.get(slug="cocody").pk],
            "availability": "Le soir", "is_available": "on",
        })
        self.assertRedirects(response, reverse("tutors:dashboard"))
        profile = TutorProfile.objects.get(user=self.user)
        self.assertTrue(profile.photo.name.endswith(".jpg"))
        with Image.open(profile.photo.path) as img:
            self.assertLessEqual(max(img.size), 600)

    def test_upload_rejects_bad_extension(self):
        self.client.get(reverse("tutors:dashboard"))
        bad = SimpleUploadedFile("script.exe", b"MZ", content_type="application/octet-stream")
        response = self.client.post(reverse("tutors:documents"), {"kind": "ID_CARD", "file": bad})
        self.assertContains(response, "Format non accepté")
        self.assertFalse(TutorDocument.objects.exists())

    def test_upload_document_is_stored_privately(self):
        self.client.get(reverse("tutors:dashboard"))
        self.client.post(reverse("tutors:documents"), {"kind": "ID_CARD", "file": pdf_file("CNI_Awa.pdf")})
        document = TutorDocument.objects.get()
        self.assertEqual(document.original_name, "CNI_Awa.pdf")
        self.assertNotIn("CNI_Awa", document.file.name)  # nom aléatoire sur le disque
        self.assertTrue(document.file.path.startswith(self.private_media_root))

    def test_submit_incomplete_profile_is_refused(self):
        self.client.get(reverse("tutors:dashboard"))
        self.client.post(reverse("tutors:submit"))
        self.assertEqual(TutorProfile.objects.get(user=self.user).status, TutorProfile.Status.DRAFT)


class VerificationTests(TempMediaTestCase):
    def setUp(self):
        self.admin = make_admin()
        self.profile = make_tutor(status=TutorProfile.Status.DRAFT)

    def test_full_verification_cycle(self):
        submit_profile(self.profile)
        self.assertEqual(self.profile.status, TutorProfile.Status.PENDING)
        self.assertTrue(Notification.objects.filter(user=self.admin).exists())

        reject_profile(self.profile, self.admin, "Diplôme illisible")
        self.assertEqual(self.profile.status, TutorProfile.Status.REJECTED)
        submit_profile(self.profile)
        approve_profile(self.profile, self.admin)
        self.assertEqual(self.profile.status, TutorProfile.Status.VERIFIED)
        self.assertEqual(self.profile.verified_by, self.admin)
        self.assertTrue(Notification.objects.filter(user=self.profile.user, title__contains="vérifié").exists())

    def test_reject_requires_reason(self):
        submit_profile(self.profile)
        with self.assertRaises(ProfileError):
            reject_profile(self.profile, self.admin, "  ")

    def test_pending_profile_cannot_be_edited(self):
        submit_profile(self.profile)
        self.client.force_login(self.profile.user)
        response = self.client.get(reverse("tutors:profile_edit"))
        self.assertRedirects(response, reverse("tutors:dashboard"))


class DocumentAccessTests(TempMediaTestCase):
    def setUp(self):
        self.profile = make_tutor()
        self.document = self.profile.documents.first()
        self.url = reverse("tutors:document_file", args=[self.document.pk])

    def test_owner_and_admin_can_view(self):
        for user in [self.profile.user, make_admin()]:
            with self.subTest(user=user.role):
                self.client.force_login(user)
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_others_get_404(self):
        for user in [make_user(), make_tutor().user]:
            with self.subTest(user=user.role):
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_anonymous_redirected_to_login(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
