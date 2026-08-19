from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class AderenciaSnapshot(models.Model):
    """Cached leadership adherence percentage for a leader within a cycle.

    Written asynchronously by Celery; dashboards read this table only
    (no synchronous recalculation on request).
    """

    lider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='aderencia_snapshots',
        verbose_name='líder',
    )
    ciclo = models.ForeignKey(
        'cycles.Ciclo',
        on_delete=models.PROTECT,
        related_name='aderencia_snapshots',
        verbose_name='ciclo',
    )
    percentual = models.DecimalField(
        'percentual',
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal('0')),
            MaxValueValidator(Decimal('100')),
        ],
        help_text='Percentual de aderência 0–100.',
    )
    componentes = models.JSONField(
        'componentes',
        default=dict,
        blank=True,
        help_text='Breakdown do cálculo de aderência.',
    )
    calculado_em = models.DateTimeField('calculado em')

    class Meta:
        verbose_name = 'snapshot de aderência'
        verbose_name_plural = 'snapshots de aderência'
        ordering = ['-calculado_em', 'lider']
        constraints = [
            models.UniqueConstraint(
                fields=['lider', 'ciclo'],
                name='unique_aderencia_lider_ciclo',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(percentual__gte=Decimal('0'))
                    & models.Q(percentual__lte=Decimal('100'))
                ),
                name='aderencia_percentual_0_100',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.lider} — {self.ciclo}: {self.percentual}%'
