# Generated manually for T026 — chave lógica de dedupe de lembretes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0001_notificacaolog'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificacaolog',
            name='referencia',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Chave do pendente (ex.: avaliacao:{id}, acao_pdi:{id}).',
                max_length=64,
                verbose_name='referência',
            ),
        ),
        migrations.AddField(
            model_name='notificacaolog',
            name='janela',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Janela do lembrete (ex.: data-alvo ISO YYYY-MM-DD).',
                max_length=32,
                verbose_name='janela',
            ),
        ),
        migrations.AddIndex(
            model_name='notificacaolog',
            index=models.Index(
                fields=['destinatario', 'tipo', 'referencia', 'janela'],
                name='notif_log_dedupe_idx',
            ),
        ),
    ]
