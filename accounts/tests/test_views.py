"""Tests de l'inscription, de la connexion et du compte."""
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from core.testing import PASSWORD, make_user


def signup_data(**overrides):
    data = {
        "first_name": "Awa", "last_name": "Koné", "email": "Awa@Exemple.ci", "phone": "07 01 02 03 04",
        "password1": PASSWORD, "password2": PASSWORD, "accept_terms": "on",
    }
    data.update(overrides)
    return data


class SignupTests(TestCase):
    def test_parent_signup_creates_parent_and_logs_in(self):
        response = self.client.post(reverse("accounts:signup_parent"), signup_data())
        self.assertRedirects(response, reverse("accounts:dashboard"), fetch_redirect_response=False)
        user = User.objects.get()
        self.assertEqual(user.role, User.Role.PARENT)
        self.assertEqual(user.email, "awa@exemple.ci")
        self.assertEqual(user.phone, "+2250701020304")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_tutor_signup_creates_tutor(self):
        self.client.post(reverse("accounts:signup_tutor"), signup_data())
        self.assertEqual(User.objects.get().role, User.Role.TUTOR)

    def test_terms_must_be_accepted(self):
        data = signup_data()
        del data["accept_terms"]
        response = self.client.post(reverse("accounts:signup_parent"), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_duplicate_phone_in_other_format_is_rejected(self):
        make_user(phone="0701020304")
        response = self.client.post(reverse("accounts:signup_parent"), signup_data(phone="+225 07 01 02 03 04"))
        self.assertContains(response, "Un compte existe déjà avec ce numéro")

    def test_invalid_phone_is_rejected(self):
        response = self.client.post(reverse("accounts:signup_parent"), signup_data(phone="0901020304"))
        self.assertContains(response, "Numéro invalide")

    def test_cannot_sign_up_as_admin(self):
        self.client.post(reverse("accounts:signup_parent"), signup_data(role="ADMIN"))
        self.assertEqual(User.objects.get().role, User.Role.PARENT)


class LoginTests(TestCase):
    def setUp(self):
        self.user = make_user(email="moussa@exemple.ci", phone="0501020304")

    def login(self, identifier, password=PASSWORD):
        return self.client.post(reverse("accounts:login"), {"username": identifier, "password": password})

    def test_login_with_email_case_insensitive(self):
        response = self.login("Moussa@Exemple.CI")
        self.assertRedirects(response, reverse("accounts:dashboard"), fetch_redirect_response=False)

    def test_login_with_phone_any_format(self):
        for identifier in ["0501020304", "05 01 02 03 04", "+225 05 01 02 03 04"]:
            with self.subTest(identifier=identifier):
                self.client.logout()
                self.assertEqual(self.login(identifier).status_code, 302)

    def test_wrong_password(self):
        response = self.login("moussa@exemple.ci", "mauvais")
        self.assertContains(response, "Identifiant ou mot de passe incorrect")

    def test_suspended_user_cannot_login(self):
        self.user.is_suspended = True
        self.user.save()
        response = self.login("moussa@exemple.ci")
        self.assertContains(response, "Votre compte est suspendu")

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.client.post(reverse("accounts:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)


class DashboardRedirectTests(TestCase):
    def test_each_role_lands_on_its_space(self):
        cases = [
            (make_user(role=User.Role.PARENT), "tutoring:parent_dashboard"),
            (make_user(role=User.Role.TUTOR), "tutors:dashboard"),
            (make_user(role=User.Role.ADMIN, is_staff=True), "backoffice:dashboard"),
        ]
        for user, target in cases:
            with self.subTest(role=user.role):
                self.client.force_login(user)
                response = self.client.get(reverse("accounts:dashboard"))
                self.assertRedirects(response, reverse(target), fetch_redirect_response=False)

    def test_anonymous_is_sent_to_login(self):
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertTrue(response.url.startswith(reverse("accounts:login")))


class AccountTests(TestCase):
    def test_update_account(self):
        user = make_user()
        self.client.force_login(user)
        response = self.client.post(reverse("accounts:account"), {
            "first_name": "Awa", "last_name": "Traoré", "email": user.email, "phone": "07 99 88 77 66"})
        self.assertRedirects(response, reverse("accounts:account"))
        user.refresh_from_db()
        self.assertEqual(user.last_name, "Traoré")
        self.assertEqual(user.phone, "+2250799887766")

    def test_password_reset_sends_email(self):
        make_user(email="reset@exemple.ci")
        self.client.post(reverse("accounts:password_reset"), {"email": "reset@exemple.ci"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/reinitialiser/", mail.outbox[0].body)
