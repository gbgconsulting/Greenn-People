"""Management command: importação one-shot de ciclos/avaliações legado Sólides.

Superfície CLI fina — valida args, chama ``import_ciclos_avaliacoes`` e emite
o relatório (stdout e opcionalmente ``--report-file``).

Ordem fixa (``contracts/import-command-contract.md`` §Semântica):
1. Parse solicitações + avaliações (pré-atomic)
2. ``transaction.atomic()``: fase 1 ciclos → fase 2 cabeçalhos agregados
3. Relatório com seções ``grupos_agregados`` / ``ids_colapsados`` / ``orfaos_*``

Códigos de saída (``contracts/import-command-contract.md`` §Códigos de saída):
- ``0`` — sucesso (persistência ok ou dry-run ok; conflitos/órfãos não-fatais ok)
- ``1`` — erro fatal pré-persistência ou de persistência:
  - args inválidos / ausentes
  - arquivo ausente ou ilegível / OOXML inválido
  - colunas obrigatórias ausentes
  - falha de migration pré-requisito (``Ciclo.solides_id`` ausente)
  - falha inesperada de persistência (``transaction.atomic`` faz rollback)
- Não há exit ``2`` nesta versão (args inválidos também → ``1``).

T017: fases 1+2 via importer na mesma atomic; relatório via
``format_ciclos_avaliacoes_report``. Sem UI/DRF/Celery; denylist intacta
(não chama stage/open/close/approval/evaluation/adherence).
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
    """CLI fina US1+US2 (T017): ciclos → cabeçalhos; relatório com
    ``grupos_agregados`` / ``ids_colapsados`` / ``orfaos_*``.
    """

    help = (
        "Importa solicitações como ciclos históricos encerrados e cabeçalhos "
        "de avaliação agregados (1:1) do backup Sólides (OOXML). "
        "Relatório inclui grupos_agregados, ids_colapsados e orfaos_*."
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
            help=(
                "Parse + agregação + totais projetados (ciclos/cabeçalhos) "
                "sem commit no banco."
            ),
        )

    def handle(self, *args, **options) -> int:
        """Parse → atomic (ciclos → cabeçalhos) → relatório mascarado.

        Persistência e ordem das fases ficam no importer; aqui só args,
        códigos de saída e emissão de ``format_ciclos_avaliacoes_report``
        (contadores + amostra ``grupos_agregados`` / ``ids_colapsados`` /
        ``orfaos_ciclo`` / ``orfaos_usuario``).
        """
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
        """Stdout obrigatório; ``--report-file`` grava o mesmo texto UTF-8."""
        self.stdout.write(text, ending="")
        if report_file:
            Path(report_file).write_text(text, encoding="utf-8")
