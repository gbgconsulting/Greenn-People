from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class PDI(TimeStampedModel):
    """Individual development plan for a collaborator."""

    class Status(models.TextChoices):
        ATIVO = 'ativo', 'Ativo'
        CONCLUIDO = 'concluido', 'Concluído'
        ARQUIVADO = 'arquivado', 'Arquivado'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='pdis',
        verbose_name='usuário',
    )
    titulo = models.CharField('título', max_length=200)
    status = models.CharField(
        'status',
        max_length=20,
        choices=Status.choices,
        default=Status.ATIVO,
    )

    class Meta:
        verbose_name = 'PDI'
        verbose_name_plural = 'PDIs'
        ordering = ['usuario', '-created_at']

    def __str__(self) -> str:
        return f'{self.titulo} ({self.usuario})'


class AcaoPDI(TimeStampedModel):
    """Development action within a PDI, with deadline and status."""

    class Status(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        EM_ANDAMENTO = 'em_andamento', 'Em andamento'
        CONCLUIDA = 'concluida', 'Concluída'
        ATRASADA = 'atrasada', 'Atrasada'

    pdi = models.ForeignKey(
        PDI,
        on_delete=models.PROTECT,
        related_name='acoes',
        verbose_name='PDI',
    )
    descricao = models.TextField('descrição')
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='acoes_pdi',
        verbose_name='responsável',
    )
    prazo = models.DateField('prazo')
    status = models.CharField(
        'status',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )

    class Meta:
        verbose_name = 'ação de PDI'
        verbose_name_plural = 'ações de PDI'
        ordering = ['prazo', 'id']

    def __str__(self) -> str:
        preview = self.descricao.strip()
        if len(preview) > 60:
            preview = f'{preview[:57]}...'
        return preview or f'Ação PDI #{self.pk}'

    def save(self, *args, **kwargs):
        """Recalcula atraso quando ``prazo`` entra no save (FR-018)."""
        raw_update_fields = kwargs.get('update_fields')
        # Materializa antes das memberships (Django aceita qualquer iterable).
        update_fields = (
            None if raw_update_fields is None else frozenset(raw_update_fields)
        )
        should_recalc = update_fields is None or 'prazo' in update_fields
        if should_recalc:
            # Import local evita ciclo com ``apps.pdi.services.overdue``.
            from apps.pdi.services.overdue import recalculate_overdue_status

            previous_status = self.status
            recalculate_overdue_status(self)
            if (
                update_fields is not None
                and self.status != previous_status
                and 'status' not in update_fields
            ):
                kwargs['update_fields'] = update_fields | {'status'}
        super().save(*args, **kwargs)
