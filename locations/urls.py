from django.urls import path

from . import views

app_name = "locations"

urlpatterns = [
    path("zones/", views.ZoneListView.as_view(), name="zones"),
    path("repetiteur-a-domicile/<slug:slug>/", views.CommuneDetailView.as_view(), name="commune"),
]
