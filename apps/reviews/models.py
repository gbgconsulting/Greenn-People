from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Avaliacao(TimeStampedModel):
    """Per-user evaluation within a performance cycle (aggregated stage)."""

    class Etapa(models.TextChoices):
        INPUT_METAS = 'input_metas', 'Input de metas'
        APROVACAO_METAS = 'aprovacao_metas', 'Aprovação de metas'
        RESULTADOS = 'resultados', 'Resultados'
        APROVACAO_RESULTADOS = 'aprovacao_resultados', 'Aprovação de resultados'
        AVALIACAO = 'avaliacao', 'Avaliação'
        FEEDBACK = 'feedback', 'Feedback'

    ciclo = models.ForeignKey(
        'cycles.Ciclo',
        on_delete=models.PROTECT,
        related_name='avaliacoes',
        verbose_name='ciclo',
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='avaliacoes',
        verbose_name='usuário',
    )
    etapa = models.CharField(
        'etapa',
        max_length=30,
        choices=Etapa.choices,
        default=Etapa.INPUT_METAS,
    )
    nota_final_lider = models.DecimalField(
        'nota final do líder',
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )
    nota_final_autoavaliacao = models.DecimalField(
        'nota final da autoavaliação',
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'avaliação'
        verbose_name_plural = 'avaliações'
        ordering = ['ciclo', 'usuario']
        unique_together = [('ciclo', 'usuario')]

    def __str__(self) -> str:
        return f'{self.usuario} — {self.ciclo} ({self.get_etapa_display()})'
