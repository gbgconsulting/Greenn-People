from django.db import models

from apps.core.models import TimeStampedModel


class ObjetivoEstrategico(TimeStampedModel):
    """Company strategic objective linked to a performance cycle."""

    descricao = models.TextField('descrição')
    ciclo = models.ForeignKey(
        'cycles.Ciclo',
        on_delete=models.PROTECT,
        related_name='objetivos_estrategicos',
        verbose_name='ciclo',
    )

    class Meta:
        verbose_name = 'objetivo estratégico'
        verbose_name_plural = 'objetivos estratégicos'
        ordering = ['ciclo', 'id']

    def __str__(self) -> str:
        preview = self.descricao.strip()
        if len(preview) > 80:
            preview = f'{preview[:77]}...'
        return preview or f'Objetivo #{self.pk}'
