from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
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


class Meta(TimeStampedModel):
    """Quantifiable goal for a collaborator, linked to a strategic objective."""

    class Status(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        APROVADA = 'aprovada', 'Aprovada'
        REPROVADA = 'reprovada', 'Reprovada'

    class StatusResultado(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        APROVADO = 'aprovado', 'Aprovado'
        REPROVADO = 'reprovado', 'Reprovado'

    # Progresso estruturado (marco binário): único conjunto aceito na gravação.
    PROGRESSO_NAO_INICIADA = Decimal('0')
    PROGRESSO_EM_ANDAMENTO = Decimal('50')
    PROGRESSO_CONCLUIDA = Decimal('100')
    PROGRESSO_BINARIO_VALORES = frozenset(
        {
            PROGRESSO_NAO_INICIADA,
            PROGRESSO_EM_ANDAMENTO,
            PROGRESSO_CONCLUIDA,
        },
    )
    PROGRESSO_BINARIO_CHOICES = (
        (PROGRESSO_NAO_INICIADA, 'Não iniciada (0%)'),
        (PROGRESSO_EM_ANDAMENTO, 'Em andamento (50%)'),
        (PROGRESSO_CONCLUIDA, 'Concluída (100%)'),
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='metas',
        verbose_name='usuário',
    )
    objetivo_estrategico = models.ForeignKey(
        ObjetivoEstrategico,
        on_delete=models.PROTECT,
        related_name='metas',
        verbose_name='objetivo estratégico',
    )
    descricao = models.TextField('descrição')
    progresso = models.DecimalField(
        'progresso',
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal('0')),
            MaxValueValidator(Decimal('100')),
        ],
        help_text=(
            'Marco binário persistido como 0, 50 ou 100; '
            'editável apenas na etapa resultados.'
        ),
    )
    status = models.CharField(
        'status',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    status_resultado = models.CharField(
        'status do resultado',
        max_length=20,
        choices=StatusResultado.choices,
        default=StatusResultado.PENDENTE,
    )

    class Meta:
        verbose_name = 'meta'
        verbose_name_plural = 'metas'
        ordering = ['objetivo_estrategico', 'usuario', 'id']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(progresso__isnull=True)
                | (
                    models.Q(progresso__gte=Decimal('0'))
                    & models.Q(progresso__lte=Decimal('100'))
                ),
                name='meta_progresso_entre_0_e_100',
            ),
        ]

    def __str__(self) -> str:
        preview = self.descricao.strip()
        if len(preview) > 60:
            preview = f'{preview[:57]}...'
        return preview or f'Meta #{self.pk}'

    def clean(self):
        super().clean()
        if self.progresso is not None and (
            self.progresso < Decimal('0') or self.progresso > Decimal('100')
        ):
            raise ValidationError(
                {'progresso': 'O progresso deve estar entre 0 e 100.'},
            )

    def progresso_binario_normalizado(self) -> Decimal | None:
        """Retorna 0/50/100 se ``progresso`` for um marco binário válido."""
        if self.progresso is None:
            return None
        for permitido in (
            self.PROGRESSO_NAO_INICIADA,
            self.PROGRESSO_EM_ANDAMENTO,
            self.PROGRESSO_CONCLUIDA,
        ):
            if self.progresso == permitido:
                return permitido
        return None

    def get_progresso_binario_label(self) -> str:
        """Rótulo de exibição do marco (sem lógica na UI)."""
        normalizado = self.progresso_binario_normalizado()
        if normalizado is None:
            if self.progresso is None:
                return '—'
            # Legado fora do conjunto binário: agrupa por faixa só para leitura.
            if self.progresso <= Decimal('0'):
                return 'Não iniciada'
            if self.progresso >= Decimal('100'):
                return 'Concluída'
            return 'Em andamento'
        labels = {
            self.PROGRESSO_NAO_INICIADA: 'Não iniciada',
            self.PROGRESSO_EM_ANDAMENTO: 'Em andamento',
            self.PROGRESSO_CONCLUIDA: 'Concluída',
        }
        return labels[normalizado]

    def get_progresso_binario_badge_status(self) -> str:
        """Status compatível com ``badge_status`` para o marco de progresso."""
        normalizado = self.progresso_binario_normalizado()
        if normalizado == self.PROGRESSO_CONCLUIDA or (
            self.progresso is not None and self.progresso >= Decimal('100')
        ):
            return 'concluida'
        if normalizado == self.PROGRESSO_EM_ANDAMENTO or (
            self.progresso is not None and self.progresso > Decimal('0')
        ):
            return 'em_andamento'
        return 'neutro'

    def mark_reprovada(self) -> None:
        """Marca a meta como reprovada (aprovação de metas)."""
        self.status = self.Status.REPROVADA

    def reopen(self) -> None:
        """FR-026: reabre meta reprovada sem retroceder a etapa agregada."""
        if self.status != self.Status.REPROVADA:
            raise ValidationError(
                {'status': 'Só é possível reabrir uma meta com status reprovada.'},
            )
        self.status = self.Status.PENDENTE

    def mark_resultado_reprovado(self) -> None:
        """Marca o resultado da meta como reprovado."""
        self.status_resultado = self.StatusResultado.REPROVADO

    def reopen_resultado(self) -> None:
        """FR-026: reabre resultado reprovado sem retroceder a etapa agregada."""
        if self.status_resultado != self.StatusResultado.REPROVADO:
            raise ValidationError(
                {
                    'status_resultado': (
                        'Só é possível reabrir um resultado com status reprovado.'
                    ),
                },
            )
        self.status_resultado = self.StatusResultado.PENDENTE
