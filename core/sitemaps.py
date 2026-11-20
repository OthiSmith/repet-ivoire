"""Plan du site (sitemap.xml) pour les moteurs de recherche."""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from locations.models import Commune


class StaticPagesSitemap(Sitemap):
    changefreq = "monthly"

    def items(self):
        return ["core:home", "core:faq", "premium:info", "locations:zones", "accounts:signup_parent", "accounts:signup_tutor",
                "core:legal_notice", "core:privacy", "core:terms"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 1.0 if item == "core:home" else 0.5


class CommuneSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Commune.objects.filter(is_active=True).order_by("slug")


SITEMAPS = {"pages": StaticPagesSitemap, "communes": CommuneSitemap}
