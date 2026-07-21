from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameModelBackend(ModelBackend):
    """Authenticate with either username or email, case-insensitively."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(get_user_model().USERNAME_FIELD)
        if username is None or password is None:
            return None

        UserModel = get_user_model()
        try:
            user = UserModel._default_manager.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
        except UserModel.DoesNotExist:
            return None
        except UserModel.MultipleObjectsReturned:
            user = (
                UserModel._default_manager.filter(
                    Q(username__iexact=username) | Q(email__iexact=username)
                )
                .order_by("pk")
                .first()
            )

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
