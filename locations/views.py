"""Pages publiques par zone : utiles aux familles et au référencement local."""
from django.db.models import Count, Prefetch, Q
from django.views.generic import DetailView, ListView

from catalog.models import Subject
from tutors.models import TutorProfile

from .models import City, Commune

VERIFIED_TUTORS = Q(
    tutors__status=TutorProfile.Status.VERIFIED, tutors__user__is_active=True, tutors__user__is_suspended=False)


class ZoneListView(ListView):
    template_name = "locations/zones.html"
    context_object_name = "cities"

    def get_queryset(self):
        communes = Commune.objects.filter(is_active=True).annotate(
            tutor_count=Count("tutors", filter=VERIFIED_TUTORS, distinct=True)).order_by("name")
        return City.objects.prefetch_related(Prefetch("communes", queryset=communes)).order_by("order", "name")


class CommuneDetailView(DetailView):
    template_name = "locations/commune.html"
    context_object_name = "commune"
    queryset = Commune.objects.filter(is_active=True).select_related("city")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tutors = TutorProfile.objects.verified().filter(communes=self.object)
        context["tutor_count"] = tutors.count()
        context["subjects"] = (
            Subject.objects.filter(tutors__in=tutors).annotate(n=Count("tutors", distinct=True)).order_by("order")
        )
        context["nearby"] = (
            Commune.objects.filter(city=self.object.city, is_active=True).exclude(pk=self.object.pk)
        )
        return context
