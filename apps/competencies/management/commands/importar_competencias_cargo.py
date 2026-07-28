"""Management command: importação one-shot do catálogo legado.

Superfície CLI fina — valida args, chama ``import_catalog`` e emite o
relatório (stdout e opcionalmente ``--report-file``).

Contrato: ``contracts/import-command-contract.md``.
"""

from __future__ import annotations

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
            raise CommandError(str(exc), returncode=1) from exc
        except EscalaInativaError as exc:
            if exc.report is not None:
                self._emit_report(format_report(exc.report), report_file)
            raise CommandError(str(exc), returncode=1) from exc

        self._emit_report(format_report(report), report_file)

    def _emit_report(self, text: str, report_file: str | None) -> None:
        self.stdout.write(text, ending="")
        if report_file:
            Path(report_file).write_text(text, encoding="utf-8")
