"""Routage principal de Répét'Ivoire."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from core.sitemaps import SITEMAPS
from core.views import robots_txt

admin.site.site_header = "Répét'Ivoire — administration technique"
admin.site.site_title = "Répét'Ivoire"
admin.site.index_title = "Administration technique"

urlpatterns = [
    # Admin Django réservé à la maintenance ; le back-office métier est sous /gestion/.
    path("admin-technique/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("robots.txt", robots_txt, name="robots"),
    path("", include("core.urls")),
    path("", include("accounts.urls")),
    path("", include("tutors.urls")),
    path("", include("tutoring.urls")),
    path("", include("notifications.urls")),
    path("", include("premium.urls")),
    path("", include("backoffice.urls")),
    path("", include("locations.urls")),
]

handler404 = "core.views.page_not_found"
handler403 = "core.views.permission_denied"

# En développement uniquement : service des médias PUBLICS.
# Le dossier private_media n'est jamais exposé.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
