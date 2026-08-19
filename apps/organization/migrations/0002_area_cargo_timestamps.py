# Generated manually for T019 — TimeStampedModel on Area/Cargo

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='area',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                verbose_name='criado em',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='area',
            name='updated_at',
            field=models.DateTimeField(
                auto_now=True,
                verbose_name='atualizado em',
            ),
        ),
        migrations.AddField(
            model_name='cargo',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                verbose_name='criado em',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='cargo',
            name='updated_at',
            field=models.DateTimeField(
                auto_now=True,
                verbose_name='atualizado em',
            ),
        ),
    ]
