from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .models import User

app_name = "accounts"

urlpatterns = [
    path("connexion/", views.LoginView.as_view(), name="login"),
    path("deconnexion/", auth_views.LogoutView.as_view(), name="logout"),
    path("inscription/", views.SignupChoiceView.as_view(), name="signup"),
    path("inscription/parent/", views.SignupView.as_view(role=User.Role.PARENT), name="signup_parent"),
    path("inscription/repetiteur/", views.SignupView.as_view(role=User.Role.TUTOR), name="signup_tutor"),
    path("mon-espace/", views.dashboard, name="dashboard"),
    path("mon-compte/", views.AccountView.as_view(), name="account"),
    path("mon-compte/mot-de-passe/", views.PasswordChangeView.as_view(), name="password_change"),
    path("mot-de-passe-oublie/", views.PasswordResetView.as_view(), name="password_reset"),
    path("mot-de-passe-oublie/envoye/", views.PasswordResetDoneView.as_view(), name="password_reset_done"),
    path("reinitialiser/<uidb64>/<token>/", views.PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("reinitialiser/termine/", views.PasswordResetCompleteView.as_view(), name="password_reset_complete"),
]
