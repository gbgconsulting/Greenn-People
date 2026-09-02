from django.conf import settings
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.generic import CreateView, FormView, TemplateView

from apps.accounts.emails import send_confirmation_email
from apps.accounts.forms import (
    EmailAuthenticationForm,
    RegisterForm,
    ResendConfirmationForm,
)
from apps.accounts.mixins import (
    LoginRateLimitMixin,
    PasswordResetRateLimitMixin,
    RegisterRateLimitMixin,
    ResendConfirmationRateLimitMixin,
)
from apps.accounts.models import CustomUser
from apps.accounts.tokens import email_confirmation_token


class RegisterView(RegisterRateLimitMixin, CreateView):
    form_class = RegisterForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:verify_email')

    def dispatch(self, request, *args, **kwargs):
        if not getattr(settings, 'REGISTRATION_ENABLED', False):
            raise Http404()
        if request.user.is_authenticated:
            return HttpResponseRedirect('/')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        send_confirmation_email(self.object, self.request)
        messages.success(
            self.request,
            'Conta criada. Verifique seu e-mail para confirmar o cadastro.',
        )
        return HttpResponseRedirect(self.get_success_url())


class VerifyEmailView(TemplateView):
    template_name = 'accounts/verify_email.html'


class ConfirmEmailView(View):
    """Validate confirmation token and set ``email_confirmado_em`` (RF-02.1)."""

    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, uidb64, token):
        user = self._get_user(uidb64)
        if user is None or not email_confirmation_token.check_token(user, token):
            messages.error(
                request,
                'Link de confirmação inválido ou expirado. Solicite um novo.',
            )
            return HttpResponseRedirect(reverse('accounts:resend_confirmation'))

        if user.email_confirmado_em is None:
            user.email_confirmado_em = timezone.now()
            user.save(update_fields=['email_confirmado_em'])

        messages.success(request, 'E-mail confirmado. Você já pode entrar.')
        return HttpResponseRedirect(reverse('accounts:login'))

    @staticmethod
    def _get_user(uidb64):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            return CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return None


class ResendConfirmationView(ResendConfirmationRateLimitMixin, FormView):
    form_class = ResendConfirmationForm
    template_name = 'accounts/resend_confirmation.html'
    success_url = reverse_lazy('accounts:verify_email')

    def form_valid(self, form):
        user = form.get_unconfirmed_user()
        if user is not None:
            send_confirmation_email(user, self.request)
        # Same message whether or not the account exists (no enumeration).
        messages.success(
            self.request,
            'Se houver uma conta pendente com este e-mail, '
            'enviamos um novo link de confirmação.',
        )
        return HttpResponseRedirect(self.get_success_url())


class LoginView(LoginRateLimitMixin, auth_views.LoginView):
    form_class = EmailAuthenticationForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('accounts:login')
    http_method_names = ['post', 'options']


class PasswordResetView(PasswordResetRateLimitMixin, auth_views.PasswordResetView):
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/email/password_reset_body.txt'
    html_email_template_name = 'accounts/email/password_reset_body.html'
    subject_template_name = 'accounts/email/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'
