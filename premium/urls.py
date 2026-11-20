from django.urls import path

from . import views

app_name = "premium"

urlpatterns = [
    path("premium/", views.PremiumInfoView.as_view(), name="info"),
    path("espace-parent/demandes/<int:pk>/premium/", views.PremiumOfferView.as_view(), name="offer"),
    path("suivi/<int:pk>/", views.TrackingView.as_view(), name="tracking"),
    path("suivi/<int:pk>/programme/", views.PlanView.as_view(), name="plan"),
    path("suivi/<int:pk>/seances/", views.SessionListView.as_view(), name="sessions"),
    path("suivi/<int:pk>/seances/nouvelle/", views.SessionCreateView.as_view(), name="session_create"),
    path("suivi/<int:pk>/notes/ajouter/", views.GradeCreateView.as_view(), name="grade_create"),
    path("suivi/<int:pk>/absence/", views.MissedSessionView.as_view(), name="missed_session"),
    path("suivi/<int:pk>/remplacement/", views.ReplacementView.as_view(), name="replacement"),
    path("suivi/<int:pk>/rapport/", views.MonthlyReportView.as_view(), name="report"),
    path("suivi/seances/<int:session_pk>/repondre/", views.SessionRespondView.as_view(), name="session_respond"),
]
