"""Formulaires de l'espace répétiteur."""
import io
from pathlib import Path

from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image, ImageOps

from catalog.models import Level, Subject
from core.forms import BootstrapFormMixin, validate_upload
from locations.models import Commune

from .models import TutorDocument, TutorProfile

PHOTO_MAX_SIZE = 600  # pixels (côté le plus long)


def resize_photo(uploaded):
    """Redresse, réduit et convertit la photo en JPEG. Supprime les métadonnées (dont la position GPS)."""
    image = ImageOps.exif_transpose(Image.open(uploaded)).convert("RGB")
    image.thumbnail((PHOTO_MAX_SIZE, PHOTO_MAX_SIZE))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85, optimize=True)
    size = buffer.tell()
    buffer.seek(0)
    name = f"{Path(uploaded.name).stem}.jpg"
    return InMemoryUploadedFile(buffer, "photo", name, "image/jpeg", size, None)


class TutorProfileForm(BootstrapFormMixin, forms.ModelForm):
    subjects = forms.ModelMultipleChoiceField(
        label="Matières enseignées", queryset=Subject.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple, required=False)
    levels = forms.ModelMultipleChoiceField(
        label="Niveaux enseignés", queryset=Level.objects.all(), widget=forms.CheckboxSelectMultiple, required=False)
    communes = forms.ModelMultipleChoiceField(
        label="Communes où vous vous déplacez", queryset=Commune.objects.filter(is_active=True).select_related("city"),
        widget=forms.CheckboxSelectMultiple, required=False)

    class Meta:
        model = TutorProfile
        fields = [
            "photo", "headline", "bio", "education", "field_of_study", "experience_years",
            "subjects", "levels", "communes", "neighborhood", "availability", "hourly_rate", "is_available",
        ]
        widgets = {
            "photo": forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png"}),
            "bio": forms.Textarea(attrs={"rows": 5}),
            "availability": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        # Nouveau fichier seulement : une photo déjà enregistrée n'a pas d'attribut content_type.
        if photo and hasattr(photo, "content_type"):
            validate_upload(photo, ["jpg", "jpeg", "png"])
            return resize_photo(photo)
        return photo


class TutorDocumentForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = TutorDocument
        fields = ["kind", "file"]
        widgets = {"file": forms.FileInput(attrs={"accept": "application/pdf,image/jpeg,image/png"})}
        help_texts = {"file": "PDF, JPG ou PNG, 5 Mo maximum. Seule l'équipe de vérification y a accès."}

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        validate_upload(uploaded, ["pdf", "jpg", "jpeg", "png"])
        return uploaded
