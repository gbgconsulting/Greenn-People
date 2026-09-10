"""Management command: ops/teste da rotina de abertura automática (018).

Invoca síncronamente ``run_auto_cycle_admission_daily`` com clock injetável
via ``--date``. **Não** substitui o Celery Beat como caminho de produção —
use só para smoke local, repro de incidentes ou dry-ops em staging.

Códigos de saída:
- ``0`` — rotina executou (qualquer status de run: sucesso/parcial/noop/falha)
- ``1`` — ``--date`` inválido ou falha inesperada ao orquestrar
"""

from __future__ import annotations

from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.cycles.tasks import run_auto_cycle_admission_daily


class Command(BaseCommand):
    help = (
        'Ops/teste: executa a rotina diária de admissão automática '
        '(mesmo núcleo da task Beat). Use --date YYYY-MM-DD para injetar '
        'o clock. Em produção o disparo primário continua sendo o Celery Beat.'
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '--date',
            dest='data_referencia',
            default=None,
            metavar='YYYY-MM-DD',
            help=(
                'Data de referência da rotina (default: hoje local). '
                'Útil para ops/teste sem alterar o schedule do Beat.'
            ),
        )

    def handle(self, *args, **options) -> None:
        raw = options.get('data_referencia')
        data_ref = self._parse_date(raw) if raw else timezone.localdate()

        self.stdout.write(
            self.style.NOTICE(
                f'Executando rotina de admissão automática '
                f'(data_referencia={data_ref.isoformat()})…'
            )
        )
        self.stdout.write(
            'Nota: este comando é ops/teste; produção usa Celery Beat '
            '(auto-cycle-admission-daily).'
        )

        try:
            result = run_auto_cycle_admission_daily(data_referencia=data_ref)
        except Exception as exc:
            raise CommandError(
                f'Falha ao executar a rotina de admissão automática: {exc}',
                returncode=1,
            ) from exc

        status = result.get('status', '?')
        run_id = result.get('run_id')
        matriculados = result.get('matriculados', 0)
        ciclo_id = result.get('ciclo_id')
        era_primeiro = result.get('era_primeiro_dia_util')

        lines = [
            f'run_id={run_id}',
            f'status={status}',
            f'data_referencia={result.get("data_referencia")}',
            f'era_primeiro_dia_util={era_primeiro}',
            f'matriculados={matriculados}',
            f'ciclo_id={ciclo_id}',
        ]
        self.stdout.write(self.style.SUCCESS('Rotina concluída:'))
        for line in lines:
            self.stdout.write(f'  {line}')

    @staticmethod
    def _parse_date(raw: str) -> date:
        try:
            return date.fromisoformat(raw)
        except ValueError as exc:
            raise CommandError(
                f'--date inválido: {raw!r} (use YYYY-MM-DD)',
                returncode=1,
            ) from exc
