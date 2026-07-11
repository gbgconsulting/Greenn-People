from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import CustomUser

ALLOWED_EMAIL_DOMAIN = 'greenn.com.br'


class RegisterForm(UserCreationForm):
    """Self-service registration restricted to the corporate e-mail domain."""

    email = forms.EmailField(
        label='E-mail',
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                'autocomplete': 'email',
                'placeholder': f'nome@{ALLOWED_EMAIL_DOMAIN}',
            },
        ),
    )
    nome = forms.CharField(
        label='Nome',
        max_length=150,
        widget=forms.TextInput(attrs={'autocomplete': 'name'}),
    )

    class Meta:
        model = CustomUser
        fields = ('nome', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'Senha'
        self.fields['password2'].label = 'Confirmação de senha'

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        domain = email.rsplit('@', 1)[-1] if '@' in email else ''
        if domain != ALLOWED_EMAIL_DOMAIN:
            raise ValidationError(
                f'Utilize um e-mail corporativo @{ALLOWED_EMAIL_DOMAIN}.',
                code='invalid_domain',
            )
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                'Já existe uma conta com este e-mail.',
                code='email_exists',
            )
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.nome = self.cleaned_data['nome']
        user.is_active = True
        user.email_confirmado_em = None
        if commit:
            user.save()
        return user


class EmailAuthenticationForm(AuthenticationForm):
    """Login by e-mail; blocks until e-mail ownership is confirmed."""

    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': _(
            'E-mail ou senha incorretos. Verifique suas credenciais.',
        ),
        'inactive': _('Esta conta está desativada.'),
        'email_not_confirmed': _(
            'Confirme seu e-mail antes de entrar. '
            'Verifique sua caixa de entrada ou reenvie o link.',
        ),
    }

    username = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(
            attrs={
                'autocomplete': 'email',
                'autofocus': True,
            },
        ),
    )

    resend_url = reverse_lazy('accounts:resend_confirmation')

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        self.fields['username'].label = 'E-mail'
        self.fields['password'].label = 'Senha'

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            self.user_cache = authenticate(
                self.request,
                username=username.strip().lower(),
                password=password,
            )
            if self.user_cache is None:
                # Distinguish unconfirmed e-mail (valid credentials) from bad login.
                try:
                    user = CustomUser.objects.get(
                        email__iexact=username.strip().lower(),
                    )
                except CustomUser.DoesNotExist:
                    raise self.get_invalid_login_error() from None
                if user.check_password(password) and user.email_confirmado_em is None:
                    raise ValidationError(
                        mark_safe(
                            f'{self.error_messages["email_not_confirmed"]} '
                            f'<a href="{self.resend_url}" class="underline '
                            f'text-emerald-700 hover:text-emerald-800">'
                            f'Reenviar confirmação</a>.'
                        ),
                        code='email_not_confirmed',
                    )
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.email_confirmado_em is None:
            raise ValidationError(
                mark_safe(
                    f'{self.error_messages["email_not_confirmed"]} '
                    f'<a href="{self.resend_url}" class="underline '
                    f'text-emerald-700 hover:text-emerald-800">'
                    f'Reenviar confirmação</a>.'
                ),
                code='email_not_confirmed',
            )


class ResendConfirmationForm(forms.Form):
    """Request a new confirmation e-mail for an unconfirmed account."""

    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={'autocomplete': 'email'}),
    )

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def get_unconfirmed_user(self):
        email = self.cleaned_data['email']
        try:
            user = CustomUser.objects.get(email__iexact=email)
        except CustomUser.DoesNotExist:
            return None
        if user.email_confirmado_em is not None:
            return None
        return user
