from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class ClassificacaoTalento(TimeStampedModel):
    """9-box talent classification for a user within a cycle.

    desempenho is derived from nota_final_lider; potencial is set manually
    by admin; quadrante is computed from the desempenho × potencial pair.
    """

    class Quadrante(models.TextChoices):
        BAIXO_BAIXO = 'baixo_baixo', 'Baixo / Baixo'
        BAIXO_MEDIO = 'baixo_medio', 'Baixo / Médio'
        BAIXO_ALTO = 'baixo_alto', 'Baixo / Alto'
        MEDIO_BAIXO = 'medio_baixo', 'Médio / Baixo'
        MEDIO_MEDIO = 'medio_medio', 'Médio / Médio'
        MEDIO_ALTO = 'medio_alto', 'Médio / Alto'
        ALTO_BAIXO = 'alto_baixo', 'Alto / Baixo'
        ALTO_MEDIO = 'alto_medio', 'Alto / Médio'
        ALTO_ALTO = 'alto_alto', 'Alto / Alto'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='classificacoes_talento',
        verbose_name='usuário',
    )
    ciclo = models.ForeignKey(
        'cycles.Ciclo',
        on_delete=models.PROTECT,
        related_name='classificacoes_talento',
        verbose_name='ciclo',
    )
    desempenho = models.PositiveSmallIntegerField(
        'desempenho',
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text='Nível 1–3 derivado da nota_final_lider normalizada.',
    )
    potencial = models.PositiveSmallIntegerField(
        'potencial',
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text='Nível 1–3 definido manualmente pelo admin.',
    )
    quadrante = models.CharField(
        'quadrante',
        max_length=20,
        choices=Quadrante.choices,
    )
    visivel_ao_colaborador = models.BooleanField(
        'visível ao colaborador',
        default=False,
    )

    class Meta:
        verbose_name = 'classificação de talento'
        verbose_name_plural = 'classificações de talento'
        ordering = ['ciclo', 'usuario']
        unique_together = [('usuario', 'ciclo')]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(desempenho__gte=1) & models.Q(desempenho__lte=3),
                name='talent_desempenho_1_3',
            ),
            models.CheckConstraint(
                condition=models.Q(potencial__gte=1) & models.Q(potencial__lte=3),
                name='talent_potencial_1_3',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.usuario} — {self.ciclo}: {self.quadrante}'
