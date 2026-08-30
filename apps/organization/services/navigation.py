"""Navegação segura de retorno em fluxos administrativos."""

from __future__ import annotations

from django.http import HttpRequest
from django.utils.http import url_has_allowed_host_and_scheme


def resolve_admin_list_return_url(
    request: HttpRequest,
    *,
    default: str,
) -> str:
    """Retorna ``next`` somente se for URL relativa permitida no host atual."""
    next_url = request.POST.get('next') or request.GET.get('next')
    if (
        next_url
        and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )
    ):
        return next_url
    return default
