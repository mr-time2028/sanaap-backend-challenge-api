"""Domain services for authentication (framework-light business logic)."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

User = get_user_model()


def request_password_reset(email: str) -> None:
    """Email a password-reset link if the user exists (silent otherwise)."""
    user = User.objects.filter(email=email).first()
    if user is None:
        return
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"/api/v1/auth/password-reset/confirm/?uid={uid}&token={token}"
    send_mail(
        subject="Password reset",
        message=f"Use this link to reset your password: {link}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def reset_password(uid: str, token: str, new_password: str) -> bool:
    """Reset the password when the uid/token pair is valid."""
    try:
        pk = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=pk)
    except (ValueError, TypeError, User.DoesNotExist):
        return False
    if not default_token_generator.check_token(user, token):
        return False
    user.set_password(new_password)
    user.save()
    return True
