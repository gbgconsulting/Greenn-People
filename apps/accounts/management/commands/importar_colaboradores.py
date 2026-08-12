"""Management command: importação one-shot de colaboradores legado Sólides.

Superfície CLI fina — valida args, chama ``import_colaboradores`` e emite o
relatório (stdout e opcionalmente ``--report-file``).

Códigos de saída (``contracts/import-command-contract.md`` §Códigos de saída):
- ``0`` — sucesso (persistência ok ou dry-run ok; conflitos não-fatais ok)
- ``1`` — erro fatal pré-persistência ou de persistência:
  - args inválidos / ausentes
  - arquivo ausente ou ilegível / OOXML inválido
  - colunas obrigatórias ausentes
  - falha inesperada de persistência (``transaction.atomic`` faz rollback)
- Não há exit ``2`` nesta versão (args inválidos também → ``1``).

Allowlist: comando + ``legacy_import``; sem UI/DRF/Celery; denylist intacta.
"""

from __future__ import annotations

import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.services.legacy_import import (
    LegacyParseError,
    format_report,
    import_colaboradores,
)


class Command(BaseCommand):
    help = (
        "Importa colaboradores, áreas e cargos do backup Sólides "
        "(OOXML) para o Greenn People. Opcionalmente resolve solides_id "
        "via planilha de avaliações (crosswalk)."
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
            "--avaliacoes",
            default=None,
            help=(
                "Path opcional do backup avaliações para crosswalk "
                "Nome Avaliado → Identificador Avaliado."
            ),
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

    def handle(self, *args, **options) -> None:
        colaboradores_path = options["colaboradores"]
        avaliacoes_path = options["avaliacoes"]
        report_file = options["report_file"]
        dry_run = options["dry_run"]

        try:
            report = import_colaboradores(
                colaboradores_path,
                avaliacoes_path=avaliacoes_path,
                dry_run=dry_run,
            )
        except LegacyParseError as exc:
            # Arquivo / OOXML / colunas — zero writes (parse pré-DB).
            raise CommandError(str(exc), returncode=1) from exc
        except Exception as exc:
            # Falha inesperada de persistência → exit 1 (atomic já fez rollback).
            raise CommandError(
                f"Falha na importação: {exc}",
                returncode=1,
            ) from exc

        self._emit_report(format_report(report), report_file)
        # Sucesso (persist ou dry-run) → exit 0 implícito do BaseCommand.

    def _emit_report(self, text: str, report_file: str | None) -> None:
        self.stdout.write(text, ending="")
        if report_file:
            Path(report_file).write_text(text, encoding="utf-8")
