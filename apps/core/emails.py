"""Shared e-mail helpers (Django-native multipart: text + HTML).

CTA and absolute URLs are resolved here from settings / request — never from
client-controlled UI state. Recipients and eligibility remain decided by the
calling service/task.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def public_base_url() -> str:
    """Canonical public origin for links in e-mails (Celery has no request)."""
    return str(getattr(settings, 'PUBLIC_BASE_URL', 'http://localhost:8000')).rstrip(
        '/',
    )


def absolute_url(path: str) -> str:
    """Join ``PUBLIC_BASE_URL`` with a path or reverse() result."""
    if not path.startswith('/'):
        path = f'/{path}'
    return urljoin(f'{public_base_url()}/', path.lstrip('/'))


def send_templated_email(
    *,
    subject: str,
    to: str,
    text_template: str,
    html_template: str,
    context: dict[str, Any],
    from_email: str | None = None,
) -> None:
    """Send one message with text/plain body and text/html alternative.

    Both bodies are rendered with Django autoescape (HTML) / plain text.
    Does not decide who may receive mail — caller supplies ``to``.
    """
    text_body = render_to_string(text_template, context)
    html_body = render_to_string(html_template, context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[to],
    )
    message.attach_alternative(html_body, 'text/html')
    message.send(fail_silently=False)
