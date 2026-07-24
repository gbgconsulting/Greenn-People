from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models


class CustomUserManager(BaseUserManager):
    """Manager that authenticates by e-mail instead of username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('O e-mail é obrigatório.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        from django.utils import timezone

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_admin', True)
        # createsuperuser skips confirmation link (RF-02.1 / Decisão #21).
        extra_fields.setdefault('email_confirmado_em', timezone.now())

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser deve ter is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser deve ter is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """Application user; login by e-mail, scoped via ``line_manager`` hierarchy."""

    username = None
    email = models.EmailField('e-mail', unique=True)
    nome = models.CharField('nome', max_length=150)
    is_admin = models.BooleanField('administrador', default=False)
    cargo = models.ForeignKey(
        'organization.Cargo',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='usuarios',
        verbose_name='cargo',
    )
    area = models.ForeignKey(
        'organization.Area',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='usuarios',
        verbose_name='área',
    )
    line_manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='direct_reports',
        verbose_name='gestor direto',
    )
    data_entrada = models.DateField('data de entrada', null=True, blank=True)
    email_confirmado_em = models.DateTimeField(
        'e-mail confirmado em',
        null=True,
        blank=True,
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']

    class Meta:
        verbose_name = 'usuário'
        verbose_name_plural = 'usuários'
        indexes = [
            models.Index(fields=['line_manager']),
            models.Index(fields=['area']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self) -> str:
        return self.nome or self.email

    @property
    def is_leader(self) -> bool:
        """True if at least one user reports directly to this user."""
        if not self.pk:
            return False
        return CustomUser.objects.filter(line_manager_id=self.pk).exists()

    @property
    def is_manager(self) -> bool:
        """True if this user leads people who themselves lead others."""
        if not self.pk or not self.is_leader:
            return False
        direct_ids = CustomUser.objects.filter(
            line_manager_id=self.pk,
        ).values_list('pk', flat=True)
        return CustomUser.objects.filter(line_manager_id__in=direct_ids).exists()

    def clean(self):
        super().clean()
        self._validate_line_manager_acyclic()
        self._validate_deactivation_without_active_reports()

    def save(self, *args, **kwargs):
        # Enforce integrity outside ModelForm (FR-028 / hierarchy cycles).
        self._validate_line_manager_acyclic()
        self._validate_deactivation_without_active_reports()
        super().save(*args, **kwargs)

    def _validate_line_manager_acyclic(self):
        if self.line_manager_id is None:
            return
        if self.pk and self.line_manager_id == self.pk:
            raise ValidationError(
                {'line_manager': 'Um usuário não pode ser gestor de si mesmo.'},
            )
        seen = {self.pk} if self.pk else set()
        current = self.line_manager
        while current is not None:
            if current.pk in seen:
                raise ValidationError(
                    {
                        'line_manager': (
                            'Gestor direto não pode criar ciclo na hierarquia.'
                        ),
                    },
                )
            seen.add(current.pk)
            current = current.line_manager

    def has_active_direct_reports(self) -> bool:
        """True if at least one active user still reports to this user."""
        if not self.pk:
            return False
        return CustomUser.objects.filter(
            line_manager_id=self.pk,
            is_active=True,
        ).exists()

    def _validate_deactivation_without_active_reports(self):
        """FR-028 / FR-011: block deactivation while active direct reports remain.

        Liberação só após reatribuição em lote completa
        (``reassign_direct_reports`` zera liderados ativos); reassign parcial
        não libera. Cada mudança de ``line_manager_id`` no lote gera AuditLog.
        """
        if self.pk is None or self.is_active:
            return
        if self.has_active_direct_reports():
            raise ValidationError(
                {
                    'is_active': (
                        'Não é possível desativar um colaborador que ainda '
                        'possui liderados ativos. Reatribua-os antes.'
                    ),
                },
            )
