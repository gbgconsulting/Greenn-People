# Generated manually for T020 — help_text de data_fim (prazo 20d / sem auto-close)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cycles', '0005_autocyclerun_autocycleevent'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ciclo',
            name='data_fim',
            field=models.DateField(
                help_text=(
                    'Prazo operacional da avaliação (automático: ativação + 20 dias '
                    'corridos). O encerramento do ciclo permanece manual — sem '
                    'auto-close hard.'
                ),
                verbose_name='data de fim',
            ),
        ),
    ]
