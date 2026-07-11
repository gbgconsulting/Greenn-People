from django.db import models


class Area(models.Model):
    """Organizational area; hierarchical via ``parent`` (cycle checks in T019)."""

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

    def __str__(self) -> str:
        return self.nome


class Cargo(models.Model):
    """Job role / seniority level."""

    nome = models.CharField('nome', max_length=100)
    nivel = models.PositiveSmallIntegerField('nível')
    is_active = models.BooleanField('ativo', default=True)

    class Meta:
        verbose_name = 'cargo'
        verbose_name_plural = 'cargos'
        ordering = ['nivel', 'nome']

    def __str__(self) -> str:
        return self.nome
