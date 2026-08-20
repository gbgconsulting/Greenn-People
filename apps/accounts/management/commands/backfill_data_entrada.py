"""Management command: backfill one-shot de ``data_entrada`` a partir do Sólides.

Superfície CLI fina — valida args, chama ``backfill_data_entrada`` e emite o
relatório (stdout e opcionalmente ``--report-file``). Sem UI de upload;
sem regra de domínio no comando.

Flags (``contracts/admission-backfill-command-contract.md``):
- ``--colaboradores`` (obrigatório)
- ``--dry-run`` / ``--report-file`` (opcionais)

Códigos de saída:
- ``0`` — sucesso operacional (persist ou dry-run; órfãos/conflitos ok)
- ``1`` — erro fatal (args / arquivo / OOXML / coluna ausente)

Não há exit ``2`` (args inválidos também → ``1``).
"""

from __future__ import annotations

import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.services.admission_backfill import backfill_data_entrada
from apps.accounts.services.legacy_import import LegacyParseError
from apps.accounts.services.legacy_import.report import (
    format_admission_backfill_report,
)


class Command(BaseCommand):
    help = (
        "Preenche data_entrada vazia a partir da coluna “Data admissão” "
        "do backup colaboradores Sólides (OOXML). Não sobrescreve datas "
        "já preenchidas; não abre/fecha ciclo."
    )

    def create_parser(self, prog_name, subcommand, **kwargs):
        """Parser que mapeia erros de args para exit ``1`` (sem exit ``2``)."""
        parser = super().create_parser(prog_name, subcommand, **kwargs)

        def error(message: str) -> None:
            if getattr(self, "_called_from_command_line", False):
                self.stderr.write(f"Error: {message}")
                sys.exit(1)
            raise CommandError(message, returncode=1)

        parser.error = error  # type: ignore[method-assign]
        return parser

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--colaboradores",
            required=True,
            help="Path do backup colaboradores (OOXML real).",
        )
        parser.add_argument(
            "--report-file",
            default=None,
            help="Se informado, grava o relatório UTF-8 neste path (além de stdout).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse + totais projetados sem commit no banco.",
        )

    def handle(self, *args, **options) -> int:
        colaboradores_path = options["colaboradores"]
        report_file = options["report_file"]
        dry_run = options["dry_run"]

        try:
            report = backfill_data_entrada(
                Path(colaboradores_path),
                dry_run=dry_run,
            )
        except LegacyParseError as exc:
            # Arquivo / OOXML / coluna “Data admissão” — zero writes.
            raise CommandError(str(exc), returncode=1) from exc
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(
                f"Falha no backfill de data_entrada: {exc}",
                returncode=1,
            ) from exc

        self._emit_report(
            format_admission_backfill_report(report),
            report_file,
        )
        return 0

    def _emit_report(self, text: str, report_file: str | None) -> None:
        self.stdout.write(text, ending="")
        if report_file:
            Path(report_file).write_text(text, encoding="utf-8")
