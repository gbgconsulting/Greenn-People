from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.accounts.tokens import email_confirmation_token


def send_confirmation_email(user, request) -> None:
    """Send e-mail confirmation link synchronously (RF-02.1 — no Celery)."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_confirmation_token.make_token(user)
    context = {
        'user': user,
        'uid': uid,
        'token': token,
        'protocol': 'https' if request.is_secure() else 'http',
        'domain': request.get_host(),
    }
    subject = render_to_string(
        'accounts/email/confirm_email_subject.txt',
        context,
    ).strip()
    body = render_to_string('accounts/email/confirm_email_body.txt', context)
    send_mail(
        subject,
        body,
        None,
        [user.email],
        fail_silently=False,
    )
