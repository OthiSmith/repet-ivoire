"""Vues publiques du socle commun."""
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Page d'accueil publique."""

    template_name = "core/home.html"


class FaqView(TemplateView):
    template_name = "core/faq.html"


class LegalNoticeView(TemplateView):
    """Mentions légales : les informations de l'éditeur viennent du fichier .env."""

    template_name = "core/legal/notice.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["legal"] = {
            "company_name": settings.LEGAL_COMPANY_NAME,
            "company_form": settings.LEGAL_COMPANY_FORM,
            "rccm": settings.LEGAL_RCCM,
            "address": settings.LEGAL_ADDRESS,
            "director": settings.LEGAL_DIRECTOR,
            "host": settings.LEGAL_HOST,
        }
        return context


class PrivacyView(TemplateView):
    template_name = "core/legal/privacy.html"


class TermsView(TemplateView):
    template_name = "core/legal/terms.html"


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin-technique/",
        "Disallow: /gestion/",
        "Disallow: /espace-parent/",
        "Disallow: /espace-repetiteur/",
        "Disallow: /mon-compte/",
        "Disallow: /notifications/",
        "Disallow: /suivi/",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def page_not_found(request, exception):
    """Page 404 personnalisée (utilisée quand DEBUG=False)."""
    return render(request, "404.html", status=404)


def permission_denied(request, exception):
    """Page 403 personnalisée (accès refusé)."""
    return render(request, "403.html", status=403)
