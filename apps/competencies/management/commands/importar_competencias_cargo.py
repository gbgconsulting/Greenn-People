"""Management command: importação one-shot do catálogo legado.

Superfície CLI fina — valida args, chama ``import_catalog`` e emite o
relatório (stdout e opcionalmente ``--report-file``).

Códigos de saída (contrato §Códigos de saída / T020–T021):
- ``0`` — sucesso (persistência ok ou dry-run ok; conflitos não-fatais ok)
- ``1`` — erro fatal pré-persistência ou de persistência:
  - args inválidos / ausentes
  - arquivo ausente ou ilegível
  - encoding inválido (não UTF-8) ou colunas obrigatórias ausentes
  - escala padrão inativa (``escala_inativa``) — relatório emitido + rollback
  - falha inesperada de persistência (``transaction.atomic`` faz rollback)
- Não há exit ``2`` nesta versão (args inválidos também → ``1``).

Contrato: ``contracts/import-command-contract.md``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.competencies.services.catalog_import import (
    CatalogParseError,
    EscalaInativaError,
    format_report,
    import_catalog,
)


class Command(BaseCommand):
    help = (
        "Importa cargos e competências das fontes legadas "
        "(lista-cargos / lista-competencias) para o catálogo ativo."
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
            "--cargos",
            required=True,
            help="Path do arquivo lista-cargos (CSV UTF-8; extensão pode ser .xlsx).",
        )
        parser.add_argument(
            "--competencias",
            required=True,
            help=(
                "Path do arquivo lista-competencias "
                "(CSV UTF-8; extensão pode ser .xlsx)."
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
        cargos_path = options["cargos"]
        competencias_path = options["competencias"]
        report_file = options["report_file"]
        dry_run = options["dry_run"]

        try:
            report = import_catalog(
                cargos_path,
                competencias_path,
                dry_run=dry_run,
            )
        except CatalogParseError as exc:
            # T021: arquivo / encoding / colunas — zero writes (parse pré-DB).
            raise CommandError(str(exc), returncode=1) from exc
        except EscalaInativaError as exc:
            # T021: escala_inativa — atomic já fez rollback; emite relatório.
            if exc.report is not None:
                self._emit_report(format_report(exc.report), report_file)
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
