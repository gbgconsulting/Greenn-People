from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class AuditLog(models.Model):
    """Append-only audit trail (one row per field change or access denial)."""

    class Acao(models.TextChoices):
        CREATE = 'create', 'Criação'
        UPDATE = 'update', 'Atualização'
        ACCESS_DENIED = 'access_denied', 'Acesso negado'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='usuário',
    )
    acao = models.CharField('ação', max_length=32, choices=Acao.choices)
    entity_type = models.CharField('tipo da entidade', max_length=100)
    entity_id = models.PositiveIntegerField('id da entidade')
    campo = models.CharField('campo', max_length=100, blank=True)
    valor_anterior = models.TextField('valor anterior', blank=True)
    valor_novo = models.TextField('valor novo', blank=True)
    created_at = models.DateTimeField('criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'log de auditoria'
        verbose_name_plural = 'logs de auditoria'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['usuario']),
            models.Index(fields=['acao']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self) -> str:
        return (
            f'{self.acao} {self.entity_type}#{self.entity_id}'
            f'.{self.campo or "-"} @ {self.created_at}'
        )

    def save(self, *args, **kwargs):
        # Append-only: existing rows cannot be updated (RF-35).
        if self.pk is not None:
            raise ValidationError('AuditLog é append-only e não pode ser alterado.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('AuditLog é append-only e não pode ser excluído.')
