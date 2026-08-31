from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from accounts.models import User

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Custom authentication backend allowing users to log in using either
    their registered Email Address or their assigned User ID (username).
    """
    def authenticate(self, request, username=None, password=None, email=None, login_id=None, **kwargs):
        identifier = login_id or email or username or kwargs.get('email')
        if not identifier or not password:
            return None

        identifier = str(identifier).strip()

        # Find user matching either email or username (case-insensitive)
        user = User.objects.filter(
            Q(email__iexact=identifier) | Q(username__iexact=identifier)
        ).first()

        if user and user.check_password(password):
            return user
        return None
