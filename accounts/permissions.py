"""Contrôles d'accès par rôle, réutilisés par toutes les applications."""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Exige un utilisateur connecté, non suspendu, qui passe `has_role()`."""

    def has_role(self, user):
        raise NotImplementedError

    def test_func(self):
        user = self.request.user
        return not user.is_suspended and self.has_role(user)


class ParentRequiredMixin(RoleRequiredMixin):
    def has_role(self, user):
        return user.is_parent


class TutorRequiredMixin(RoleRequiredMixin):
    def has_role(self, user):
        return user.is_tutor


class PlatformAdminRequiredMixin(RoleRequiredMixin):
    def has_role(self, user):
        return user.is_platform_admin or user.is_staff
