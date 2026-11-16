"""Outils de formulaires partagés : rendu Bootstrap et validation des fichiers."""
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms.renderers import TemplatesSetting


class BootstrapFormRenderer(TemplatesSetting):
    """Rend `{{ form }}` avec les gabarits Bootstrap de templates/forms/."""

    form_template_name = "forms/form.html"
    field_template_name = "forms/field.html"


class BootstrapFormMixin:
    """Ajoute les classes CSS Bootstrap aux widgets et marque les champs en erreur."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxSelectMultiple, forms.RadioSelect, forms.CheckboxInput)):
                css = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css = "form-select"
            else:
                css = "form-control"
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} {css}".strip()

    def full_clean(self):
        # Après validation seulement : ne pas déclencher la validation depuis __init__.
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                widget = self.fields[name].widget
                widget.attrs["class"] = f"{widget.attrs.get('class', '')} is-invalid".strip()


def validate_upload(uploaded, allowed_extensions):
    """Vérifie l'extension et la taille d'un fichier téléversé."""
    name = uploaded.name.lower()
    if not any(name.endswith(f".{ext}") for ext in allowed_extensions):
        raise ValidationError(
            "Format non accepté. Formats autorisés : %(formats)s.",
            params={"formats": ", ".join(ext.upper() for ext in allowed_extensions)},
            code="invalid_extension",
        )
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if uploaded.size > max_bytes:
        raise ValidationError(
            "Fichier trop volumineux (%(max)s Mo maximum).",
            params={"max": settings.MAX_UPLOAD_SIZE_MB},
            code="file_too_large",
        )
