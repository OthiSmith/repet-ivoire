from django.urls import path

from . import views

app_name = "tutors"

urlpatterns = [
    path("espace-repetiteur/", views.DashboardView.as_view(), name="dashboard"),
    path("espace-repetiteur/profil/", views.ProfileEditView.as_view(), name="profile_edit"),
    path("espace-repetiteur/justificatifs/", views.DocumentsView.as_view(), name="documents"),
    path("espace-repetiteur/justificatifs/<int:pk>/supprimer/", views.DocumentDeleteView.as_view(), name="document_delete"),
    path("espace-repetiteur/soumettre/", views.SubmitProfileView.as_view(), name="submit"),
    path("justificatifs/<int:pk>/", views.DocumentFileView.as_view(), name="document_file"),
]
