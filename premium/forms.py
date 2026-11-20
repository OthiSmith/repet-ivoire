from django import forms
from django.utils import timezone

from core.forms import BootstrapFormMixin

from .models import Grade, PlanItem, Session, Subscription

DATE_WIDGET = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
MONTH_CHOICES = [(1, "1 mois"), (3, "3 mois (un trimestre)"), (6, "6 mois"), (9, "9 mois (année scolaire)")]


class PremiumRequestForm(BootstrapFormMixin, forms.Form):
    months = forms.TypedChoiceField(label="Durée", choices=MONTH_CHOICES, coerce=int, initial=3)


class SubscriptionFormMixin:
    """Limite les matières et les chapitres à ceux de l'abonnement."""

    def __init__(self, *args, subscription, **kwargs):
        self.subscription = subscription
        super().__init__(*args, **kwargs)
        if "subject" in self.fields:
            self.fields["subject"].queryset = subscription.request.subjects.all()
            self.fields["subject"].empty_label = None

    def clean_date(self):
        day = self.cleaned_data["date"]
        if day > timezone.localdate():
            raise forms.ValidationError("La date ne peut pas être dans le futur.")
        if self.subscription.starts_on and day < self.subscription.starts_on:
            raise forms.ValidationError(
                f"Le suivi a commencé le {self.subscription.starts_on:%d/%m/%Y}.")
        return day


class SessionForm(SubscriptionFormMixin, BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Session
        fields = ["date", "duration_minutes", "status", "plan_items", "content", "homework", "engagement",
                  "tutor_comment"]
        widgets = {
            "date": DATE_WIDGET,
            "plan_items": forms.CheckboxSelectMultiple,
            "content": forms.Textarea(attrs={"rows": 3, "placeholder": "Ex. : exercices sur le théorème de Thalès, correction du devoir…"}),
            "homework": forms.Textarea(attrs={"rows": 2}),
            "tutor_comment": forms.Textarea(attrs={"rows": 2}),
            "engagement": forms.Select(choices=[("", "—"), (1, "1 — Très peu impliqué"), (2, "2"), (3, "3 — Correct"),
                                                (4, "4"), (5, "5 — Très impliqué")]),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Le répétiteur ne se déclare pas lui-même absent : c'est le parent qui le signale.
        self.fields["status"].choices = [c for c in Session.Status.choices if c[0] != Session.Status.TUTOR_ABSENT]
        self.fields["plan_items"].queryset = self.subscription.plan_items.select_related("subject")
        self.fields["plan_items"].label_from_instance = lambda item: f"{item.subject} — {item.title}"
        self.fields["date"].initial = timezone.localdate()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") == Session.Status.DONE and not cleaned.get("content"):
            self.add_error("content", "Décrivez brièvement le travail effectué.")
        return cleaned


class PlanItemForm(SubscriptionFormMixin, BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = PlanItem
        fields = ["subject", "title"]


class GradeForm(SubscriptionFormMixin, BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Grade
        fields = ["subject", "date", "kind", "score", "out_of", "comment"]
        widgets = {"date": DATE_WIDGET, "score": forms.NumberInput(attrs={"step": "0.25", "min": 0})}

    def clean_date(self):
        # Une note peut dater d'avant le début du suivi (point de départ) : seul le futur est refusé.
        day = self.cleaned_data["date"]
        if day > timezone.localdate():
            raise forms.ValidationError("La date ne peut pas être dans le futur.")
        return day

    def clean(self):
        cleaned = super().clean()
        score, out_of = cleaned.get("score"), cleaned.get("out_of")
        if score is not None and out_of and score > out_of:
            self.add_error("score", f"La note ne peut pas dépasser {out_of}.")
        return cleaned


class SessionResponseForm(BootstrapFormMixin, forms.Form):
    issue = forms.ChoiceField(label="Problème", choices=[("", "Choisir")] + Session.Issue.choices, required=False)
    comment = forms.CharField(label="Commentaire (facultatif)", required=False, max_length=1000,
                              widget=forms.Textarea(attrs={"rows": 2}))


class MissedSessionForm(SubscriptionFormMixin, BootstrapFormMixin, forms.Form):
    date = forms.DateField(label="Date de la séance manquée", widget=DATE_WIDGET)
    comment = forms.CharField(label="Commentaire (facultatif)", required=False, max_length=1000,
                              widget=forms.Textarea(attrs={"rows": 2}))


class ReplacementForm(BootstrapFormMixin, forms.Form):
    message = forms.CharField(label="Que se passe-t-il ?", max_length=2000, widget=forms.Textarea(attrs={"rows": 3}))


class ActivationForm(BootstrapFormMixin, forms.Form):
    months = forms.TypedChoiceField(label="Durée", choices=MONTH_CHOICES, coerce=int)
    amount = forms.IntegerField(label="Montant reçu (FCFA)", min_value=0, required=False)
    payment_method = forms.ChoiceField(label="Moyen de paiement", choices=[("", "—")] + Subscription.PaymentMethod.choices,
                                       required=False)
    payment_reference = forms.CharField(label="Référence de la transaction", max_length=80, required=False)
