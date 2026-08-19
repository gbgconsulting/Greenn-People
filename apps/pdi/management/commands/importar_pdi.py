"""Management command: importação one-shot de PDIs/ações legado Sólides.

Superfície CLI fina — valida args, chama ``import_pdi`` e emite o
relatório (stdout e opcionalmente ``--report-file``).

Ordem fixa (``contracts/import-command-contract.md`` §Semântica):
1. Parse ``--pdi`` (pré-atomic; openpyxl só em ``parse_xlsx``)
2. ``data_carga`` congelada no importer
3. ``--dry-run``: parse + resolve + totais projetados; **zero**
   ``save``/``create``/``update`` (T019)
4. Senão ``transaction.atomic()`` no importer: 1 PDI + 1 ação por linha;
   exceção → rollback + exit ``1``
5. Relatório via ``format_pdi_report`` — stdout **==** ``--report-file``

Códigos de saída (``contracts/import-command-contract.md`` §Códigos de saída):
- ``0`` — sucesso (persistência ok ou dry-run ok; conflitos/órfãos não-fatais ok)
- ``1`` — erro fatal pré-persistência ou de persistência:
  - args inválidos / ausentes
  - arquivo ausente ou ilegível / OOXML inválido
  - colunas obrigatórias ausentes
  - falha inesperada de persistência (``transaction.atomic`` faz rollback)
- Não há exit ``2`` nesta versão (args inválidos também → ``1``).

T009: CLI fina US1 (persistência 1+1). Sem regra de domínio aqui.
T012: órfãos / ``id_vs_nome`` saem no relatório via ``format_pdi_report``
e **não** viram exit ``1`` (não-fatais). Inatividade não é filtrada aqui.
T019: ``--dry-run`` funcional (zero writes); falha pré-persistência e
rollback de persistência → exit ``1``.

Sem UI/DRF/Celery; denylist intacta (não chama stage/open/close/approval/
``get_visible_users`` / ``user_in_scope`` / ``ScopedObjectMixin`` /
``mark_overdue_pdi_actions`` / ``calculate_pdi_progress``).
**MUST NOT** herdar ``ScopedObjectMixin``; só ``BaseCommand``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.pdi.services.legacy_import import (
    LegacyParseError,
    LegacyPersistError,
    LegacySchemaError,
    format_pdi_report,
    import_pdi,
)


class Command(BaseCommand):
    """CLI fina T009/T012/T019: ``--pdi`` + relatório mascarado; exit 0|1.

    Resolução de pessoa e persistência ficam no serviço. Este comando
    **não** autoriza por escopo: sem ``get_visible_users``, sem
    ``user_in_scope``, sem ``ScopedObjectMixin``.
    """

    help = (
        'Importa PDIs e uma ação por linha do backup Sólides (OOXML) para o '
        'Greenn People. Relatório inclui pdis_*/acoes_*/orfaos_*/conflitos.'
    )

    def create_parser(self, prog_name, subcommand, **kwargs):
        """Parser que mapeia erros de args para exit ``1`` (sem exit ``2``)."""
        parser = super().create_parser(prog_name, subcommand, **kwargs)

        def error(message: str) -> None:
            if getattr(self, '_called_from_command_line', False):
                self.stderr.write(f'Error: {message}')
                sys.exit(1)
            raise CommandError(message, returncode=1)

        parser.error = error  # type: ignore[method-assign]
        return parser

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '--pdi',
            required=True,
            help='Path do backup de PDI (OOXML real, backup_pdi_*.xlsx).',
        )
        parser.add_argument(
            '--report-file',
            default=None,
            help='Se informado, grava o relatório UTF-8 neste path (além de stdout).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help=(
                'Parse + totais projetados; zero save/create/update '
                '(T019: parse + totais projetados; zero save/create/update).'
            ),
        )

    def handle(self, *args, **options) -> int:
        """Args → importer (1 PDI + 1 ação) → relatório mascarado.

        Persistência, de-para e resolução de pessoa ficam no serviço.
        Órfãos e ``id_vs_nome`` já vêm no ``ImportReport`` — exit ``0``.
        Aqui só args, códigos de saída e emissão de ``format_pdi_report``.
        """
        pdi_path = options['pdi']
        report_file = options['report_file']
        dry_run = options['dry_run']

        try:
            report = import_pdi(pdi_path, dry_run=dry_run)
        except LegacyParseError as exc:
            raise CommandError(str(exc), returncode=1) from exc
        except LegacySchemaError as exc:
            raise CommandError(str(exc), returncode=1) from exc
        except LegacyPersistError as exc:
            raise CommandError(
                f'Falha na persistência: {exc}',
                returncode=1,
            ) from exc
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(
                f'Falha na importação: {exc}',
                returncode=1,
            ) from exc

        self._emit_report(format_pdi_report(report), report_file)
        return 0

    def _emit_report(self, text: str, report_file: str | None) -> None:
        """Stdout obrigatório; ``--report-file`` grava o **mesmo** texto UTF-8.

        NÃO loga linha XLSX crua, título, objetivo, nome ou e-mail.
        """
        self.stdout.write(text, ending='')
        if report_file:
            Path(report_file).write_text(text, encoding='utf-8')
