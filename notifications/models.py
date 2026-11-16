"""Notifications internes affichées dans l'espace de chaque utilisateur."""
from django.conf import settings
from django.db import models


class NotificationQuerySet(models.QuerySet):
    def unread(self):
        return self.filter(read_at__isnull=True)


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField("titre", max_length=160)
    body = models.TextField("message", blank=True)
    url = models.CharField("lien", max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField("lue le", null=True, blank=True)

    objects = NotificationQuerySet.as_manager()

    class Meta:
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def is_read(self):
        return self.read_at is not None
