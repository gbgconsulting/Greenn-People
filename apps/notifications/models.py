from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class NotificacaoLog(models.Model):
    """Immutable log of each e-mail send attempt (RF-31)."""

    class Tipo(models.TextChoices):
        LEMBRETE_ETAPA = 'lembrete_etapa', 'Lembrete de etapa'
        LEMBRETE_PDI = 'lembrete_pdi', 'Lembrete de ação PDI'
        FEEDBACK_CONTINUO = 'feedback_continuo', 'Feedback contínuo'
        ATRASO_PDI = 'atraso_pdi', 'Atraso de ação PDI'
        DIGEST_PDI_ATRASOS = 'digest_pdi_atrasos', 'Digest de PDIs atrasados'
        ALERTA_CICLO_AINDA_ABERTO = (
            'alerta_ciclo_ainda_aberto',
            'Alerta ciclo ainda aberto',
        )

    class Status(models.TextChoices):
        ENVIADO = 'enviado', 'Enviado'
        FALHA = 'falha', 'Falha'

    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='notificacao_logs',
        verbose_name='destinatário',
    )
    tipo = models.CharField('tipo', max_length=32, choices=Tipo.choices)
    referencia = models.CharField(
        'referência',
        max_length=64,
        blank=True,
        default='',
        help_text='Chave do pendente (ex.: avaliacao:{id}, acao_pdi:{id}).',
    )
    janela = models.CharField(
        'janela',
        max_length=32,
        blank=True,
        default='',
        help_text='Janela do lembrete (ex.: data-alvo ISO YYYY-MM-DD).',
    )
    status = models.CharField('status', max_length=16, choices=Status.choices)
    erro = models.TextField('erro', blank=True)
    created_at = models.DateTimeField('criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'log de notificação'
        verbose_name_plural = 'logs de notificação'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['destinatario']),
            models.Index(fields=['tipo']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(
                fields=['destinatario', 'tipo', 'referencia', 'janela'],
                name='notif_log_dedupe_idx',
            ),
        ]

    def __str__(self) -> str:
        return (
            f'{self.tipo} → {self.destinatario_id} '
            f'[{self.status}] @ {self.created_at}'
        )

    def save(self, *args, **kwargs):
        # Append-only after creation — no updates to existing rows.
        if self.pk is not None:
            raise ValidationError(
                'NotificacaoLog é imutável e não pode ser alterado.',
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            'NotificacaoLog é imutável e não pode ser excluído.',
        )


def already_sent(destinatario, tipo: str, referencia: str, janela: str) -> bool:
    """True if an ``enviado`` log exists for the logical reminder key."""
    destinatario_id = getattr(destinatario, 'pk', destinatario)
    return NotificacaoLog.objects.filter(
        destinatario_id=destinatario_id,
        tipo=tipo,
        referencia=referencia,
        janela=janela,
        status=NotificacaoLog.Status.ENVIADO,
    ).exists()
