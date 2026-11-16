from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import ListView

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    template_name = "notifications/list.html"
    context_object_name = "notifications"
    paginate_by = 30

    def get_queryset(self):
        return self.request.user.notifications.all()


class NotificationOpenView(LoginRequiredMixin, View):
    """Marque la notification comme lue puis suit son lien."""

    def get(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        if not notification.is_read:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        if notification.url and url_has_allowed_host_and_scheme(notification.url, allowed_hosts={request.get_host()}):
            return redirect(notification.url)
        return redirect("notifications:list")


class MarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        request.user.notifications.unread().update(read_at=timezone.now())
        return redirect("notifications:list")
