"""
Modèle utilisateur personnalisé de Répét'Ivoire.

Il doit exister AVANT la toute première migration du projet : Django ne
permet pas de changer de modèle utilisateur une fois la base créée.

Un utilisateur se connecte avec son e-mail OU son téléphone (le backend
dédié sera ajouté en phase 3). Son rôle détermine l'espace auquel il accède.
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from core.validators import normalize_ci_phone, validate_ci_phone


class UserManager(BaseUserManager):
    """Gestionnaire créant des utilisateurs identifiés par leur e-mail."""

    use_in_migrations = True

    def _create_user(self, email, phone, password, **extra_fields):
        if not email:
            raise ValueError("L'adresse e-mail est obligatoire.")
        if not phone:
            raise ValueError("Le numéro de téléphone est obligatoire.")
        email = self.normalize_email(email).lower()
        phone = normalize_ci_phone(phone)
        user = self.model(email=email, phone=phone, **extra_fields)
        user.set_password(password)  # hachage PBKDF2 géré par Django
        user.save(using=self._db)
        return user

    def create_user(self, email, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", User.Role.PARENT)
        return self._create_user(email, phone, password, **extra_fields)

    def create_superuser(self, email, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)
        if extra_fields.get("is_staff") is not True or extra_fields.get("is_superuser") is not True:
            raise ValueError("Un superutilisateur doit avoir is_staff=True et is_superuser=True.")
        return self._create_user(email, phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Compte utilisateur unique pour les parents, répétiteurs et administrateurs."""

    class Role(models.TextChoices):
        PARENT = "PARENT", "Parent"
        TUTOR = "TUTOR", "Répétiteur"
        ADMIN = "ADMIN", "Administrateur"

    email = models.EmailField("adresse e-mail", unique=True)
    phone = models.CharField(
        "téléphone",
        max_length=14,
        unique=True,
        validators=[validate_ci_phone],
        help_text="Format international : +225XXXXXXXXXX",
    )
    first_name = models.CharField("prénom", max_length=80)
    last_name = models.CharField("nom", max_length=80)
    role = models.CharField("rôle", max_length=10, choices=Role.choices, default=Role.PARENT, db_index=True)

    is_active = models.BooleanField(
        "actif",
        default=True,
        help_text="Décocher pour désactiver le compte sans le supprimer.",
    )
    is_suspended = models.BooleanField("suspendu", default=False, db_index=True)
    suspension_reason = models.TextField("motif de suspension", blank=True)
    is_staff = models.BooleanField(
        "accès administration",
        default=False,
        help_text="Autorise l'accès au back-office.",
    )
    date_joined = models.DateTimeField("date d'inscription", default=timezone.now, db_index=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["phone", "first_name", "last_name"]

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}>"

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email).lower()

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    # Raccourcis de rôle utilisés dans les vues et les gabarits.
    @property
    def is_parent(self):
        return self.role == self.Role.PARENT

    @property
    def is_tutor(self):
        return self.role == self.Role.TUTOR

    @property
    def is_platform_admin(self):
        return self.role == self.Role.ADMIN or self.is_superuser
