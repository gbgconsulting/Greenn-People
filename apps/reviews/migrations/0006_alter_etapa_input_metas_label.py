# Generated manually — rótulo UI de input_metas: "Input de metas" → "Metas"

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0005_backfill_avaliacao_concluida'),
    ]

    operations = [
        migrations.AlterField(
            model_name='avaliacao',
            name='etapa',
            field=models.CharField(
                choices=[
                    ('input_metas', 'Metas'),
                    ('aprovacao_metas', 'Aprovação de metas'),
                    ('resultados', 'Resultados'),
                    ('aprovacao_resultados', 'Aprovação de resultados'),
                    ('avaliacao', 'Avaliação'),
                    ('feedback', 'Feedback'),
                ],
                default='input_metas',
                max_length=30,
                verbose_name='etapa',
            ),
        ),
    ]
