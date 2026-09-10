from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel


class Ciclo(TimeStampedModel):
    """Performance review cycle; multiple cycles may be ``aberto`` concurrently."""

    class Status(models.TextChoices):
        ABERTO = 'aberto', 'Aberto'
        ENCERRADO = 'encerrado', 'Encerrado'

    class Origem(models.TextChoices):
        MANUAL = 'manual', 'Manual'
        AUTOMATICO = 'automatico', 'Automático'

    nome = models.CharField('nome', max_length=100)
    data_inicio = models.DateField('data de início')
    data_fim = models.DateField(
        'data de fim',
        help_text=(
            'Prazo operacional da avaliação (automático: ativação + 20 dias '
            'corridos). O encerramento do ciclo permanece manual — sem '
            'auto-close hard.'
        ),
    )
    status = models.CharField(
        'status',
        max_length=20,
        choices=Status.choices,
        default=Status.ENCERRADO,
    )
    origem = models.CharField(
        'origem',
        max_length=20,
        choices=Origem.choices,
        default=Origem.MANUAL,
    )
    marco_competencia = models.DateField(
        'marco de competência',
        null=True,
        blank=True,
        help_text=(
            'Para ciclos automáticos: sempre o dia 1 do mês de marco '
            '(YYYY-MM-01). Nulo em ciclos manuais.'
        ),
    )
    solides_id = models.CharField(
        'ID Sólides',
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
    )
    admitidos_ate = models.DateField(
        'admitidos até',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'ciclo'
        verbose_name_plural = 'ciclos'
        ordering = ['-data_inicio', 'nome']
        constraints = [
            models.UniqueConstraint(
                fields=['marco_competencia'],
                condition=models.Q(
                    origem='automatico',
                    marco_competencia__isnull=False,
                ),
                name='unique_ciclo_automatico_marco_competencia',
            ),
        ]

    def __str__(self) -> str:
        return self.nome

    @property
    def prazo_estourado(self) -> bool:
        """Atraso real pós-``data_fim`` com ciclo ainda aberto (rose na UI)."""
        from apps.cycles.services.prazo import is_prazo_estourado

        return is_prazo_estourado(self)

    def clean(self):
        super().clean()
        self._validate_date_range()

    def save(self, *args, **kwargs):
        self._validate_date_range()
        super().save(*args, **kwargs)

    def _validate_date_range(self):
        """``data_fim`` must be on or after ``data_inicio``."""
        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError(
                {
                    'data_fim': (
                        'A data de fim deve ser igual ou posterior '
                        'à data de início.'
                    ),
                },
            )


class AutoCycleRun(TimeStampedModel):
    """Operational record of one daily auto-cycle admission routine pass."""

    class Status(models.TextChoices):
        SUCESSO = 'sucesso', 'Sucesso'
        NOOP = 'noop', 'No-op'
        PARCIAL = 'parcial', 'Parcial'
        FALHA = 'falha', 'Falha'

    executado_em = models.DateTimeField('executado em')
    data_referencia = models.DateField('data de referência')
    era_primeiro_dia_util = models.BooleanField(
        'era primeiro dia útil',
        default=False,
    )
    marco_competencia = models.DateField(
        'marco de competência',
        null=True,
        blank=True,
        help_text='Preenchido se a rotina tentou ou abriu coorte no mês.',
    )
    ciclo = models.ForeignKey(
        Ciclo,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='auto_cycle_runs',
        verbose_name='ciclo',
    )
    status = models.CharField(
        'status',
        max_length=20,
        choices=Status.choices,
        default=Status.NOOP,
    )
    matriculados = models.PositiveIntegerField('matriculados', default=0)
    alertas_ciclo_aberto = models.PositiveIntegerField(
        'alertas ciclo aberto',
        default=0,
    )
    excluidos_sem_admissao = models.PositiveIntegerField(
        'excluídos sem admissão',
        default=0,
    )
    mensagem = models.TextField('mensagem', blank=True, default='')

    class Meta:
        verbose_name = 'execução automática de ciclo'
        verbose_name_plural = 'execuções automáticas de ciclo'
        ordering = ['-executado_em', '-id']

    def __str__(self) -> str:
        return (
            f'AutoCycleRun {self.data_referencia} '
            f'[{self.status}] @ {self.executado_em}'
        )


class AutoCycleEvent(models.Model):
    """Append-only business audit line for an ``AutoCycleRun``."""

    class Tipo(models.TextChoices):
        MATRICULA = 'matricula', 'Matrícula'
        ALERTA_CICLO_ABERTO = 'alerta_ciclo_aberto', 'Alerta ciclo aberto'
        PENDENCIA_SEM_ADMISSAO = (
            'pendencia_sem_admissao',
            'Pendência sem admissão',
        )
        FALHA = 'falha', 'Falha'
        NOOP_DIA = 'noop_dia', 'No-op do dia'
        COORTE_CRIADA = 'coorte_criada', 'Coorte criada'
        COORTE_REUSADA = 'coorte_reusada', 'Coorte reusada'

    run = models.ForeignKey(
        AutoCycleRun,
        on_delete=models.PROTECT,
        related_name='events',
        verbose_name='execução',
    )
    tipo = models.CharField('tipo', max_length=32, choices=Tipo.choices)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='auto_cycle_events',
        verbose_name='usuário',
    )
    ciclo = models.ForeignKey(
        Ciclo,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='auto_cycle_events',
        verbose_name='ciclo',
    )
    payload = models.JSONField('payload', default=dict, blank=True)
    criado_em = models.DateTimeField('criado em', auto_now_add=True)

    class Meta:
        verbose_name = 'evento automático de ciclo'
        verbose_name_plural = 'eventos automáticos de ciclo'
        ordering = ['-criado_em', '-id']
        indexes = [
            models.Index(fields=['run', 'tipo']),
            models.Index(fields=['tipo']),
            models.Index(fields=['criado_em']),
        ]

    def __str__(self) -> str:
        return f'{self.tipo} run={self.run_id} @ {self.criado_em}'

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValidationError(
                'AutoCycleEvent é append-only e não pode ser alterado.',
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            'AutoCycleEvent é append-only e não pode ser excluído.',
        )
