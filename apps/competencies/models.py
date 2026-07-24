from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampedModel


class Escala(TimeStampedModel):
    """Reusable rating scale with min/max and per-level labels."""

    nome = models.CharField('nome', max_length=100)
    valor_minimo = models.IntegerField('valor mínimo')
    valor_maximo = models.IntegerField('valor máximo')
    rotulos_por_nivel = models.JSONField(
        'rótulos por nível',
        default=dict,
        blank=True,
        help_text='Mapa nível → rótulo (ex.: {"1": "Iniciante", "5": "Expert"}).',
    )
    is_active = models.BooleanField('ativa', default=True)

    class Meta:
        verbose_name = 'escala'
        verbose_name_plural = 'escalas'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['nome'],
                condition=models.Q(is_active=True),
                name='unique_escala_nome_ativa',
            ),
        ]

    def __str__(self) -> str:
        return self.nome

    def clean(self):
        super().clean()
        self._validate_range()

    def save(self, *args, **kwargs):
        self._validate_range()
        super().save(*args, **kwargs)

    def _validate_range(self):
        if (
            self.valor_minimo is not None
            and self.valor_maximo is not None
            and self.valor_maximo <= self.valor_minimo
        ):
            raise ValidationError(
                {
                    'valor_maximo': (
                        'O valor máximo deve ser maior que o valor mínimo.'
                    ),
                },
            )


class Competencia(TimeStampedModel):
    """Competency evaluated against a rating scale."""

    class Tipo(models.TextChoices):
        TECNICA = 'tecnica', 'Técnica'
        COMPORTAMENTAL = 'comportamental', 'Comportamental'
        LIDERANCA = 'lideranca', 'Liderança'

    nome = models.CharField('nome', max_length=150)
    descricao = models.TextField('descrição', blank=True)
    tipo = models.CharField(
        'tipo',
        max_length=20,
        choices=Tipo.choices,
    )
    escala = models.ForeignKey(
        Escala,
        on_delete=models.PROTECT,
        related_name='competencias',
        verbose_name='escala',
    )
    is_active = models.BooleanField('ativa', default=True)

    class Meta:
        verbose_name = 'competência'
        verbose_name_plural = 'competências'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['nome'],
                condition=models.Q(is_active=True),
                name='unique_competencia_nome_ativa',
            ),
        ]

    def __str__(self) -> str:
        return self.nome


class CargoCompetencia(TimeStampedModel):
    """Expected competency level and weight for a job role."""

    cargo = models.ForeignKey(
        'organization.Cargo',
        on_delete=models.PROTECT,
        related_name='cargo_competencias',
        verbose_name='cargo',
    )
    competencia = models.ForeignKey(
        Competencia,
        on_delete=models.PROTECT,
        related_name='cargo_competencias',
        verbose_name='competência',
    )
    nivel_esperado = models.DecimalField(
        'nível esperado',
        max_digits=8,
        decimal_places=2,
    )
    peso = models.DecimalField(
        'peso',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )

    class Meta:
        verbose_name = 'competência do cargo'
        verbose_name_plural = 'competências do cargo'
        ordering = ['cargo', 'competencia']
        constraints = [
            models.UniqueConstraint(
                fields=['cargo', 'competencia'],
                name='unique_cargo_competencia',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.cargo} — {self.competencia}'

    def clean(self):
        super().clean()
        if self.peso is not None and self.peso <= 0:
            raise ValidationError(
                {'peso': 'O peso deve ser maior que zero.'},
            )
