"""Formulaires d'inscription, de connexion et de gestion du compte."""
from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    BaseUserCreationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
)
from django.urls import reverse
from django.utils.safestring import mark_safe

from core.forms import BootstrapFormMixin
from core.validators import normalize_ci_phone

from .models import User

PHONE_WIDGET = forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "tel", "placeholder": "07 01 02 03 04"})
UNIQUE_ERRORS = {
    "email": {"unique": "Un compte existe déjà avec cette adresse e-mail."},
    "phone": {"unique": "Un compte existe déjà avec ce numéro de téléphone."},
}


def phone_field(**kwargs):
    """Champ plus long que le modèle : on accepte « +225 07 01 02 03 04 » avant normalisation.

    Un champ déclaré explicitement ne reçoit pas Meta.error_messages : on lui passe le message d'unicité.
    """
    return forms.CharField(label="Téléphone", max_length=25, widget=PHONE_WIDGET,
                           error_messages=UNIQUE_ERRORS["phone"], **kwargs)


class PhoneEmailCleanMixin:
    """Normalise l'e-mail (minuscules) et le téléphone (+225XXXXXXXXXX)."""

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_phone(self):
        return normalize_ci_phone(self.cleaned_data["phone"])


class SignupForm(BootstrapFormMixin, PhoneEmailCleanMixin, BaseUserCreationForm):
    phone = phone_field(help_text="Numéro ivoirien à 10 chiffres.")
    accept_terms = forms.BooleanField(
        required=True,
        error_messages={"required": "Vous devez accepter les conditions pour créer un compte."},
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone")
        error_messages = UNIQUE_ERRORS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.pop("autofocus", None)
        self.fields["first_name"].widget.attrs.update(autofocus=True, autocomplete="given-name")
        self.fields["last_name"].widget.attrs["autocomplete"] = "family-name"
        self.fields["email"].widget.attrs["autocomplete"] = "email"
        self.fields["password1"].help_text = "8 caractères minimum, pas uniquement des chiffres."
        self.fields["accept_terms"].label = mark_safe(
            f'J\'accepte les <a href="{reverse("core:terms")}" target="_blank">conditions d\'utilisation</a> '
            f'et la <a href="{reverse("core:privacy")}" target="_blank">politique de confidentialité</a>.'
        )


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    error_messages = {
        "invalid_login": "Identifiant ou mot de passe incorrect.",
        "inactive": "Ce compte est désactivé.",
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["username"].label = "E-mail ou téléphone"
        self.fields["username"].max_length = 254
        self.fields["username"].widget.attrs.update(autocomplete="username", placeholder="vous@exemple.ci ou 07 01 02 03 04")

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.is_suspended:
            raise forms.ValidationError(
                "Votre compte est suspendu. Contactez-nous pour en savoir plus.", code="suspended"
            )


class AccountForm(BootstrapFormMixin, PhoneEmailCleanMixin, forms.ModelForm):
    phone = phone_field()

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone")
        error_messages = UNIQUE_ERRORS


class StyledPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    pass


class StyledPasswordResetForm(BootstrapFormMixin, PasswordResetForm):
    pass


class StyledSetPasswordForm(BootstrapFormMixin, SetPasswordForm):
    pass
