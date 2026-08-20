"""Management command: backfill one-shot de ``data_entrada`` a partir do Sólides.

Superfície CLI fina — valida args e delega a
``admission_backfill.backfill_data_entrada``. Sem UI de upload.

Flags (``contracts/admission-backfill-command-contract.md``):
- ``--colaboradores`` (obrigatório)
- ``--dry-run`` / ``--report-file`` (opcionais)

Exit: ``0`` sucesso operacional; ``1`` erro fatal (arquivo/OOXML/coluna).
Stub T003 — implementação completa em T029.
"""

from __future__ import annotations

import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.services.admission_backfill import backfill_data_entrada


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
        # Stub T003: superfície CLI pronta; domínio em NotImplementedError até T029.
        backfill_data_entrada(
            Path(options["colaboradores"]),
            dry_run=options["dry_run"],
        )
        return 0
