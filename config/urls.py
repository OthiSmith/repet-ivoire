"""Routage principal de Répét'Ivoire."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Répét'Ivoire — administration technique"
admin.site.site_title = "Répét'Ivoire"
admin.site.index_title = "Administration technique"

urlpatterns = [
    # Admin Django réservé à la maintenance (le back-office métier arrivera en phase 6).
    path("admin-technique/", admin.site.urls),
    path("", include("core.urls")),
]

handler404 = "core.views.page_not_found"
handler403 = "core.views.permission_denied"

# En développement uniquement : service des médias PUBLICS.
# Le dossier private_media n'est jamais exposé.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
