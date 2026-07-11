from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailConfirmationTokenGenerator(PasswordResetTokenGenerator):
    """Token invalidated once ``email_confirmado_em`` is set (RF-02.1)."""

    def _make_hash_value(self, user, timestamp):
        email_confirmed = (
            '' if user.email_confirmado_em is None else str(user.email_confirmado_em)
        )
        return f'{user.pk}{user.password}{email_confirmed}{timestamp}'


email_confirmation_token = EmailConfirmationTokenGenerator()
