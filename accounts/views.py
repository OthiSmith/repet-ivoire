"""Inscription, connexion et gestion du compte."""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView, UpdateView

from .forms import (
    AccountForm,
    LoginForm,
    SignupForm,
    StyledPasswordChangeForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
)
from .models import User


class SignupChoiceView(TemplateView):
    template_name = "accounts/signup_choice.html"


class SignupView(CreateView):
    """Inscription commune : le rôle est fixé par l'URL (parent ou répétiteur)."""

    form_class = SignupForm
    template_name = "accounts/signup.html"
    role = User.Role.PARENT

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["role"] = self.role
        context["is_tutor_signup"] = self.role == User.Role.TUTOR
        return context

    def form_valid(self, form):
        form.instance.role = self.role
        user = form.save()
        login(self.request, user, backend="accounts.backends.EmailOrPhoneBackend")
        messages.success(self.request, f"Bienvenue {user.first_name} ! Votre compte a été créé.")
        return redirect("accounts:dashboard")


class LoginView(auth_views.LoginView):
    form_class = LoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


@login_required
def dashboard(request):
    """Point d'entrée « Mon espace » : redirige selon le rôle."""
    user = request.user
    if user.is_platform_admin or user.is_staff:
        return redirect("backoffice:dashboard")
    if user.is_tutor:
        return redirect("tutors:dashboard")
    return redirect("tutoring:parent_dashboard")


class AccountView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = AccountForm
    template_name = "accounts/account.html"
    success_url = reverse_lazy("accounts:account")
    success_message = "Vos informations ont été mises à jour."

    def get_object(self, queryset=None):
        return self.request.user


class PasswordChangeView(SuccessMessageMixin, auth_views.PasswordChangeView):
    form_class = StyledPasswordChangeForm
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:account")
    success_message = "Votre mot de passe a été modifié."


class PasswordResetView(auth_views.PasswordResetView):
    form_class = StyledPasswordResetForm
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/emails/password_reset.txt"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    form_class = StyledSetPasswordForm
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"
