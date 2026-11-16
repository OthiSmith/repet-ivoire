def unread_notifications(request):
    """Nombre de notifications non lues, affiché sur la cloche de la barre de navigation."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {"unread_notifications_count": user.notifications.unread().count()}
