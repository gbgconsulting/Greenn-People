# Generated manually — flag de envio da autoavaliação + backfill legado.

from django.db import migrations, models
from django.db.models import Exists, OuterRef


def forwards_backfill_autoavaliacao_enviada(apps, schema_editor):
    Avaliacao = apps.get_model('reviews', 'Avaliacao')
    AvaliacaoCompetencia = apps.get_model('reviews', 'AvaliacaoCompetencia')

    linha_sem_nota = AvaliacaoCompetencia.objects.filter(
        avaliacao_id=OuterRef('pk'),
        nota_autoavaliacao__isnull=True,
    )
    tem_linha = AvaliacaoCompetencia.objects.filter(avaliacao_id=OuterRef('pk'))

    qs = (
        Avaliacao.objects.filter(autoavaliacao_enviada=False)
        .annotate(_tem_linha=Exists(tem_linha), _incompleta=Exists(linha_sem_nota))
        .filter(_tem_linha=True, _incompleta=False)
    )
    qs.update(autoavaliacao_enviada=True)


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0007_add_solides_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='avaliacao',
            name='autoavaliacao_enviada',
            field=models.BooleanField(
                default=False,
                help_text=(
                    'True quando o colaborador enviou a autoavaliação; '
                    'bloqueia novas edições na etapa de avaliação.'
                ),
                verbose_name='autoavaliação enviada',
            ),
        ),
        migrations.AddField(
            model_name='avaliacao',
            name='autoavaliacao_enviada_em',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='autoavaliação enviada em',
            ),
        ),
        migrations.RunPython(
            forwards_backfill_autoavaliacao_enviada,
            backwards_noop,
        ),
    ]
