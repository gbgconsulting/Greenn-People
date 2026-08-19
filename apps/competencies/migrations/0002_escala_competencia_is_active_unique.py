# Generated manually for T016 — soft-delete + unicidade entre ativos

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('competencies', '0001_escala_competencia_cargocompetencia'),
    ]

    operations = [
        migrations.AddField(
            model_name='escala',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='ativa'),
        ),
        migrations.AddField(
            model_name='competencia',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='ativa'),
        ),
        migrations.AddConstraint(
            model_name='escala',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_active', True)),
                fields=('nome',),
                name='unique_escala_nome_ativa',
            ),
        ),
        migrations.AddConstraint(
            model_name='competencia',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_active', True)),
                fields=('nome',),
                name='unique_competencia_nome_ativa',
            ),
        ),
    ]
