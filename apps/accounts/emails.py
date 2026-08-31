from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.accounts.tokens import email_confirmation_token
from apps.core.emails import send_templated_email


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
    send_templated_email(
        subject=subject,
        to=user.email,
        text_template='accounts/email/confirm_email_body.txt',
        html_template='accounts/email/confirm_email_body.html',
        context=context,
    )
