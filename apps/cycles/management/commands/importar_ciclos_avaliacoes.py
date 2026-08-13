"""Management command: importação one-shot de ciclos/avaliações legado Sólides.

Superfície CLI fina — valida args, chama ``import_ciclos_avaliacoes`` e emite
o relatório (stdout e opcionalmente ``--report-file``).

Códigos de saída (``contracts/import-command-contract.md`` §Códigos de saída):
- ``0`` — sucesso (persistência ok ou dry-run ok; conflitos/órfãos não-fatais ok)
- ``1`` — erro fatal pré-persistência ou de persistência:
  - args inválidos / ausentes
  - arquivo ausente ou ilegível / OOXML inválido
  - colunas obrigatórias ausentes
  - falha de migration pré-requisito (``Ciclo.solides_id`` ausente)
  - falha inesperada de persistência (``transaction.atomic`` faz rollback)
- Não há exit ``2`` nesta versão (args inválidos também → ``1``).

T012: fase 1 ciclos funcional via importer; fase 2 cabeçalhos stub até US2.
Sem UI/DRF/Celery; denylist intacta (não chama stage/open/close/approval).
"""

from __future__ import annotations

import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.cycles.services.legacy_import import (
    LegacyParseError,
    LegacyPersistError,
    LegacySchemaError,
    format_ciclos_avaliacoes_report,
    import_ciclos_avaliacoes,
)


class Command(BaseCommand):
    help = (
        "Importa solicitações como ciclos históricos encerrados e cabeçalhos "
        "de avaliação do backup Sólides (OOXML) para o Greenn People."
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
            "--solicitacoes",
            required=True,
            help="Path do backup de solicitações (OOXML real).",
        )
        parser.add_argument(
            "--avaliacoes",
            required=True,
            help="Path do backup de avaliações — cabeçalhos (OOXML real).",
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
        solicitacoes_path = options["solicitacoes"]
        avaliacoes_path = options["avaliacoes"]
        report_file = options["report_file"]
        dry_run = options["dry_run"]

        try:
            report = import_ciclos_avaliacoes(
                solicitacoes_path,
                avaliacoes_path,
                dry_run=dry_run,
            )
        except LegacyParseError as exc:
            raise CommandError(str(exc), returncode=1) from exc
        except LegacySchemaError as exc:
            raise CommandError(str(exc), returncode=1) from exc
        except LegacyPersistError as exc:
            raise CommandError(
                f"Falha na persistência: {exc}",
                returncode=1,
            ) from exc
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(
                f"Falha na importação: {exc}",
                returncode=1,
            ) from exc

        self._emit_report(format_ciclos_avaliacoes_report(report), report_file)
        return 0

    def _emit_report(self, text: str, report_file: str | None) -> None:
        self.stdout.write(text, ending="")
        if report_file:
            Path(report_file).write_text(text, encoding="utf-8")
