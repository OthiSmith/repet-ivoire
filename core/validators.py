"""Validateurs réutilisables dans tout le projet."""
import re

from django.core.exceptions import ValidationError

# Depuis 2021, les numéros ivoiriens comptent 10 chiffres.
# Mobiles : 01 (Moov), 05 (MTN), 07 (Orange) ; fixes : 21, 25, 27.
_CI_PHONE_RE = re.compile(r"^(01|05|07|21|25|27)\d{8}$")


def normalize_ci_phone(value: str) -> str:
    """
    Normalise un numéro ivoirien au format international « +225XXXXXXXXXX ».

    Accepte les espaces, tirets, points et les préfixes +225 / 00225.
    Lève ValidationError si le numéro n'est pas valide.
    """
    if value is None:
        raise ValidationError("Le numéro de téléphone est obligatoire.")
    digits = re.sub(r"[\s\-.()]", "", str(value))
    if digits.startswith("+225"):
        digits = digits[4:]
    elif digits.startswith("00225"):
        digits = digits[5:]
    if not _CI_PHONE_RE.match(digits):
        raise ValidationError(
            "Numéro invalide. Saisissez un numéro ivoirien à 10 chiffres "
            "(ex. : 07 01 02 03 04).",
            code="invalid_phone",
        )
    return f"+225{digits}"


def validate_ci_phone(value: str) -> None:
    """Validateur de modèle : vérifie qu'un numéro est déjà normalisé."""
    if not re.match(r"^\+225(01|05|07|21|25|27)\d{8}$", value or ""):
        raise ValidationError("Numéro de téléphone ivoirien invalide.", code="invalid_phone")
