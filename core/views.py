"""Vues publiques du socle commun."""
from django.shortcuts import render
from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Page d'accueil publique."""

    template_name = "core/home.html"


def page_not_found(request, exception):
    """Page 404 personnalisée (utilisée quand DEBUG=False)."""
    return render(request, "404.html", status=404)


def permission_denied(request, exception):
    """Page 403 personnalisée (accès refusé)."""
    return render(request, "403.html", status=403)
