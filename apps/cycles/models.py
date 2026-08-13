from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel


class Ciclo(TimeStampedModel):
    """Performance review cycle; at most one may be ``aberto`` at a time."""

    class Status(models.TextChoices):
        ABERTO = 'aberto', 'Aberto'
        ENCERRADO = 'encerrado', 'Encerrado'

    nome = models.CharField('nome', max_length=100)
    data_inicio = models.DateField('data de início')
    data_fim = models.DateField(
        'data de fim',
        help_text='Informativo; o encerramento é manual.',
    )
    status = models.CharField(
        'status',
        max_length=20,
        choices=Status.choices,
        default=Status.ENCERRADO,
    )
    solides_id = models.CharField(
        'ID Sólides',
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
    )

    class Meta:
        verbose_name = 'ciclo'
        verbose_name_plural = 'ciclos'
        ordering = ['-data_inicio', 'nome']

    def __str__(self) -> str:
        return self.nome

    def clean(self):
        super().clean()
        self._validate_single_open()

    def save(self, *args, **kwargs):
        self._validate_single_open()
        super().save(*args, **kwargs)

    def _validate_single_open(self):
        """Application constraint: only one cycle with status ``aberto``."""
        if self.status != self.Status.ABERTO:
            return
        qs = Ciclo.objects.filter(status=self.Status.ABERTO)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError(
                {
                    'status': (
                        'Já existe um ciclo aberto. '
                        'Encerre-o antes de abrir outro.'
                    ),
                },
            )
