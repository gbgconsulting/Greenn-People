"""Mixins de segurança para views de autenticação."""

from __future__ import annotations

from django.conf import settings
from django.contrib import messages

from apps.core.ratelimit import get_client_ip, increment, is_over_limit


class RateLimitedFormMixin:
    """Limita POSTs por IP (e chaves extras) via cache."""

    rate_limit_scope: str = 'form'

    def _rate_limit_keys(self, request) -> list[str]:
        return [f'{self.rate_limit_scope}:ip:{get_client_ip(request)}']

    def _rate_limit_max(self) -> int:
        return 5

    def _rate_limit_period(self) -> int:
        return 60

    def _rate_limit_blocked_response(self, request):
        messages.error(
            request,
            'Muitas tentativas. Aguarde alguns minutos e tente novamente.',
        )
        if hasattr(self, 'get_form'):
            return self.render_to_response(self.get_context_data(form=self.get_form()))
        return self.render_to_response(self.get_context_data())

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            limit = self._rate_limit_max()
            period = self._rate_limit_period()
            keys = self._rate_limit_keys(request)
            if any(is_over_limit(key, limit, period) for key in keys):
                return self._rate_limit_blocked_response(request)
            for key in keys:
                increment(key, period)
        return super().dispatch(request, *args, **kwargs)


class LoginRateLimitMixin(RateLimitedFormMixin):
    rate_limit_scope = 'login'

    def _rate_limit_max(self) -> int:
        return settings.RATE_LIMIT_LOGIN

    def _rate_limit_period(self) -> int:
        return settings.RATE_LIMIT_LOGIN_PERIOD

    def _rate_limit_keys(self, request) -> list[str]:
        keys = super()._rate_limit_keys(request)
        email = (request.POST.get('username') or '').strip().lower()
        if email:
            keys.append(f'login:email:{email}')
        return keys


class PasswordResetRateLimitMixin(RateLimitedFormMixin):
    rate_limit_scope = 'password_reset'

    def _rate_limit_max(self) -> int:
        return settings.RATE_LIMIT_PASSWORD_RESET

    def _rate_limit_period(self) -> int:
        return settings.RATE_LIMIT_PASSWORD_RESET_PERIOD

    def _rate_limit_keys(self, request) -> list[str]:
        keys = super()._rate_limit_keys(request)
        email = (request.POST.get('email') or '').strip().lower()
        if email:
            keys.append(f'password_reset:email:{email}')
        return keys


class RegisterRateLimitMixin(RateLimitedFormMixin):
    rate_limit_scope = 'register'

    def _rate_limit_max(self) -> int:
        return settings.RATE_LIMIT_REGISTER

    def _rate_limit_period(self) -> int:
        return settings.RATE_LIMIT_REGISTER_PERIOD

    def _rate_limit_keys(self, request) -> list[str]:
        keys = super()._rate_limit_keys(request)
        email = (request.POST.get('email') or '').strip().lower()
        if email:
            keys.append(f'register:email:{email}')
        return keys


class ResendConfirmationRateLimitMixin(RateLimitedFormMixin):
    rate_limit_scope = 'resend_confirmation'

    def _rate_limit_max(self) -> int:
        return settings.RATE_LIMIT_RESEND_CONFIRMATION

    def _rate_limit_period(self) -> int:
        return settings.RATE_LIMIT_RESEND_CONFIRMATION_PERIOD

    def _rate_limit_keys(self, request) -> list[str]:
        keys = super()._rate_limit_keys(request)
        email = (request.POST.get('email') or '').strip().lower()
        if email:
            keys.append(f'resend_confirmation:email:{email}')
        return keys
