from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("questions-frequentes/", views.FaqView.as_view(), name="faq"),
    path("mentions-legales/", views.LegalNoticeView.as_view(), name="legal_notice"),
    path("confidentialite/", views.PrivacyView.as_view(), name="privacy"),
    path("conditions-utilisation/", views.TermsView.as_view(), name="terms"),
]
