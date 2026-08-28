# Generated manually — aderência neutra (sem obrigações) usa percentual NULL.

from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_aderenciasnapshot'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='aderenciasnapshot',
            name='aderencia_percentual_0_100',
        ),
        migrations.AlterField(
            model_name='aderenciasnapshot',
            name='percentual',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text=(
                    'Percentual de aderência 0–100; NULL = neutro '
                    '(sem obrigações no escopo).'
                ),
                max_digits=5,
                null=True,
                verbose_name='percentual',
            ),
        ),
        migrations.AddConstraint(
            model_name='aderenciasnapshot',
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(percentual__isnull=True)
                    | (
                        models.Q(percentual__gte=Decimal('0'))
                        & models.Q(percentual__lte=Decimal('100'))
                    )
                ),
                name='aderencia_percentual_0_100_or_null',
            ),
        ),
    ]
