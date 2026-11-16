"""Backend d'authentification : connexion avec l'e-mail OU le numéro de téléphone."""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ValidationError

from core.validators import normalize_ci_phone


class EmailOrPhoneBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(get_user_model().USERNAME_FIELD)
        if not username or password is None:
            return None
        user = self._find_user(username.strip())
        if user is None:
            # Hachage factice : même durée de réponse qu'un compte existant.
            get_user_model()().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    @staticmethod
    def _find_user(identifier):
        User = get_user_model()
        if "@" in identifier:
            return User.objects.filter(email__iexact=identifier).first()
        try:
            phone = normalize_ci_phone(identifier)
        except ValidationError:
            return None
        return User.objects.filter(phone=phone).first()
