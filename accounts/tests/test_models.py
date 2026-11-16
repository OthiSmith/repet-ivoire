"""Tests du modèle utilisateur personnalisé."""
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user_defaults_to_parent_and_hashes_password(self):
        user = User.objects.create_user(
            email="Awa.Kone@Exemple.CI", phone="07 01 02 03 04",
            password="MotDePasse!2026", first_name="Awa", last_name="Koné",
        )
        self.assertEqual(user.email, "awa.kone@exemple.ci")
        self.assertEqual(user.phone, "+2250701020304")
        self.assertEqual(user.role, User.Role.PARENT)
        self.assertTrue(user.is_parent)
        self.assertFalse(user.is_staff)
        self.assertNotEqual(user.password, "MotDePasse!2026")
        self.assertTrue(user.check_password("MotDePasse!2026"))

    def test_create_superuser_is_admin(self):
        admin = User.objects.create_superuser(
            email="admin@exemple.ci", phone="0501020304", password="MotDePasse!2026",
            first_name="Admin", last_name="Plateforme",
        )
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_platform_admin)

    def test_email_and_phone_are_unique(self):
        User.objects.create_user(email="a@exemple.ci", phone="0701020304", password="x", first_name="A", last_name="B")
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email="b@exemple.ci", phone="+225 07 01 02 03 04", password="x", first_name="C", last_name="D")

    def test_invalid_phone_is_rejected(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            User.objects.create_user(email="c@exemple.ci", phone="123", password="x", first_name="A", last_name="B")
