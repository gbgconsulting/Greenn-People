# Generated manually for T017 — unicidade de nome entre Area/Cargo ativos

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0002_area_cargo_timestamps'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='area',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_active', True)),
                fields=('nome',),
                name='unique_area_nome_ativa',
            ),
        ),
        migrations.AddConstraint(
            model_name='cargo',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_active', True)),
                fields=('nome',),
                name='unique_cargo_nome_ativo',
            ),
        ),
    ]
