from django.urls import path

from . import views

app_name = "backoffice"

urlpatterns = [
    path("gestion/", views.DashboardView.as_view(), name="dashboard"),
    path("gestion/repetiteurs/", views.TutorListView.as_view(), name="tutor_list"),
    path("gestion/repetiteurs/<int:pk>/", views.TutorReviewView.as_view(), name="tutor_review"),
    path("gestion/demandes/", views.RequestListView.as_view(), name="request_list"),
    path("gestion/demandes/<int:pk>/", views.RequestDetailView.as_view(), name="request_detail"),
    path("gestion/premium/", views.PremiumListView.as_view(), name="premium_list"),
    path("gestion/premium/<int:pk>/", views.PremiumDetailView.as_view(), name="premium_detail"),
    path("gestion/programme/", views.CurriculumView.as_view(), name="curriculum"),
]
