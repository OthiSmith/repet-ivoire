from django import forms

from catalog.models import Subject
from core.forms import BootstrapFormMixin
from locations.models import Commune

from .models import TutoringRequest


class TutoringRequestForm(BootstrapFormMixin, forms.ModelForm):
    subjects = forms.ModelMultipleChoiceField(
        label="Matières", queryset=Subject.objects.filter(is_active=True), widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Choisissez au moins une matière."})
    commune = forms.ModelChoiceField(
        label="Commune", queryset=Commune.objects.filter(is_active=True).select_related("city"),
        empty_label="Choisir une commune")

    class Meta:
        model = TutoringRequest
        fields = ["child_first_name", "level", "subjects", "commune", "neighborhood", "sessions_per_week",
                  "availability", "goals", "budget_monthly"]
        widgets = {
            "availability": forms.Textarea(attrs={"rows": 2, "placeholder": "Ex. : lundi et jeudi de 17 h à 19 h"}),
            "goals": forms.Textarea(attrs={"rows": 3}),
            "neighborhood": forms.TextInput(attrs={"placeholder": "Ex. : Riviera 2, Angré, Sideci…"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["level"].empty_label = "Choisir une classe"


class RespondForm(BootstrapFormMixin, forms.Form):
    message = forms.CharField(
        label="Un mot pour la famille (facultatif)", required=False, max_length=1000,
        widget=forms.Textarea(attrs={"rows": 2}))
