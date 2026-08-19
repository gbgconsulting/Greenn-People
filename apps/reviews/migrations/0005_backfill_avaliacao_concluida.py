# Generated manually for T059 — backfill concluida from existing feedback acks.

from django.db import migrations
from django.db.models import Exists, OuterRef


def forwards_backfill_concluida(apps, schema_editor):
    Avaliacao = apps.get_model('reviews', 'Avaliacao')
    Feedback = apps.get_model('reviews', 'Feedback')
    feedback_ciente = Feedback.objects.filter(
        avaliacao_id=OuterRef('pk'),
        tipo='lider',
        ciente_em__isnull=False,
    )
    ids = list(
        Avaliacao.objects.annotate(_ok=Exists(feedback_ciente))
        .filter(_ok=True, concluida=False)
        .values_list('pk', flat=True),
    )
    if ids:
        Avaliacao.objects.filter(pk__in=ids).update(concluida=True)


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0004_avaliacao_concluida'),
    ]

    operations = [
        migrations.RunPython(forwards_backfill_concluida, backwards_noop),
    ]
