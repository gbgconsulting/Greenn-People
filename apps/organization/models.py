from django.core.exceptions import ValidationError
from django.db import models

from apps.core.models import TimeStampedModel


class Area(TimeStampedModel):
    """Organizational area; hierarchical via ``parent`` (acyclic)."""

    nome = models.CharField('nome', max_length=100)
    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='subareas',
        verbose_name='área pai',
    )
    is_active = models.BooleanField('ativa', default=True)

    class Meta:
        verbose_name = 'área'
        verbose_name_plural = 'áreas'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['nome'],
                condition=models.Q(is_active=True),
                name='unique_area_nome_ativa',
            ),
        ]

    def __str__(self) -> str:
        return self.nome

    def clean(self):
        super().clean()
        self._validate_parent_acyclic()

    def save(self, *args, **kwargs):
        # Enforce integrity outside ModelForm (hierarchy cycles).
        self._validate_parent_acyclic()
        super().save(*args, **kwargs)

    def _validate_parent_acyclic(self):
        if self.parent_id is None:
            return
        if self.pk and self.parent_id == self.pk:
            raise ValidationError(
                {'parent': 'Uma área não pode ser pai de si mesma.'},
            )
        seen = {self.pk} if self.pk else set()
        current = self.parent
        while current is not None:
            if current.pk in seen:
                raise ValidationError(
                    {
                        'parent': (
                            'Área pai não pode criar ciclo na hierarquia.'
                        ),
                    },
                )
            seen.add(current.pk)
            current = current.parent


class Cargo(TimeStampedModel):
    """Job role / seniority level."""

    nome = models.CharField('nome', max_length=100)
    nivel = models.PositiveSmallIntegerField('nível')
    is_active = models.BooleanField('ativo', default=True)

    class Meta:
        verbose_name = 'cargo'
        verbose_name_plural = 'cargos'
        ordering = ['nivel', 'nome']
        constraints = [
            models.UniqueConstraint(
                fields=['nome'],
                condition=models.Q(is_active=True),
                name='unique_cargo_nome_ativo',
            ),
        ]

    def __str__(self) -> str:
        return self.nome
