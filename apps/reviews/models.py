from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel

_SNAPSHOT_FIELDS = ('peso_utilizado', 'nivel_esperado_utilizado')


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
    concluida = models.BooleanField(
        'concluída',
        default=False,
        help_text=(
            'True quando feedback do líder tem ciente_em; '
            'congelado no encerramento do ciclo para o indicador de conclusão.'
        ),
    )

    class Meta:
        verbose_name = 'avaliação'
        verbose_name_plural = 'avaliações'
        ordering = ['ciclo', 'usuario']
        unique_together = [('ciclo', 'usuario')]

    def __str__(self) -> str:
        return f'{self.usuario} — {self.ciclo} ({self.get_etapa_display()})'


class AvaliacaoCompetencia(TimeStampedModel):
    """Per-competency scores within an evaluation; weight/expected level are snapshots."""

    avaliacao = models.ForeignKey(
        Avaliacao,
        on_delete=models.PROTECT,
        related_name='linhas_competencia',
        verbose_name='avaliação',
    )
    competencia = models.ForeignKey(
        'competencies.Competencia',
        on_delete=models.PROTECT,
        related_name='avaliacoes_competencia',
        verbose_name='competência',
    )
    nota_autoavaliacao = models.DecimalField(
        'nota da autoavaliação',
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    nota_lider = models.DecimalField(
        'nota do líder',
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    peso_utilizado = models.DecimalField(
        'peso utilizado',
        max_digits=8,
        decimal_places=2,
        help_text='Snapshot write-once do peso do cargo no momento da avaliação.',
    )
    nivel_esperado_utilizado = models.DecimalField(
        'nível esperado utilizado',
        max_digits=8,
        decimal_places=2,
        help_text='Snapshot write-once do nível esperado no momento da avaliação.',
    )

    class Meta:
        verbose_name = 'avaliação de competência'
        verbose_name_plural = 'avaliações de competência'
        ordering = ['avaliacao', 'competencia']
        constraints = [
            models.UniqueConstraint(
                fields=['avaliacao', 'competencia'],
                name='unique_avaliacao_competencia',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.avaliacao} — {self.competencia}'

    def save(self, *args, **kwargs):
        if self.pk:
            previous = (
                AvaliacaoCompetencia.objects.filter(pk=self.pk)
                .values(*_SNAPSHOT_FIELDS)
                .first()
            )
            if previous is not None:
                errors = {}
                for field in _SNAPSHOT_FIELDS:
                    if previous[field] != getattr(self, field):
                        errors[field] = (
                            'Campo snapshot é write-once e não pode ser alterado.'
                        )
                if errors:
                    raise ValidationError(errors)
        super().save(*args, **kwargs)


class Feedback(TimeStampedModel):
    """Structured feedback linked to an evaluation; ack tracked via ciente_em."""

    class Tipo(models.TextChoices):
        COLABORADOR = 'colaborador', 'Colaborador'
        LIDER = 'lider', 'Líder'

    avaliacao = models.ForeignKey(
        Avaliacao,
        on_delete=models.PROTECT,
        related_name='feedbacks',
        verbose_name='avaliação',
    )
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='feedbacks_autorados',
        verbose_name='autor',
    )
    tipo = models.CharField(
        'tipo',
        max_length=20,
        choices=Tipo.choices,
    )
    conteudo = models.TextField('conteúdo')
    ciente_em = models.DateTimeField(
        'ciente em',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'feedback'
        verbose_name_plural = 'feedbacks'
        ordering = ['-created_at', 'id']

    def __str__(self) -> str:
        return f'{self.get_tipo_display()} — {self.avaliacao}'
