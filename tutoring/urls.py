from django.urls import path

from . import views

app_name = "tutoring"

urlpatterns = [
    path("espace-parent/", views.ParentDashboardView.as_view(), name="parent_dashboard"),
    path("espace-parent/demandes/nouvelle/", views.RequestCreateView.as_view(), name="request_create"),
    path("espace-parent/demandes/<int:pk>/", views.RequestDetailView.as_view(), name="request_detail"),
    path("espace-parent/demandes/<int:pk>/annuler/", views.RequestCancelView.as_view(), name="request_cancel"),
    path("espace-parent/propositions/<int:pk>/choisir/", views.ProposalChooseView.as_view(), name="proposal_choose"),
    path("espace-repetiteur/propositions/<int:pk>/", views.TutorProposalView.as_view(), name="tutor_proposal"),
]
