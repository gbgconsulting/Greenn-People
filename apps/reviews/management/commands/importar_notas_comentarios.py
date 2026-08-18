"""Management command: importação one-shot de notas/comentários legado Sólides.

Superfície CLI fina — valida args, chama ``import_notas_comentarios`` e emite
o relatório (stdout e opcionalmente ``--report-file``).

Ordem fixa (``contracts/import-command-contract.md`` §Semântica):
1. Parse notas + comentários (pré-atomic; openpyxl só em ``parse_xlsx``)
2. Rebuild do mapa ``--avaliacoes`` em memória (011; **zero** upsert de cabeçalho)
3. ``transaction.atomic()``: fase Notas → ``calcular_nota_final_*`` →
   fase Comentários (T014: as duas fases na **mesma** atomic)
4. Relatório via ``format_notas_comentarios_report`` — seções
   ``comentarios_criados`` / ``comentarios_inalterados`` / ``orfaos_autor``

Códigos de saída (``contracts/import-command-contract.md`` §Códigos de saída):
- ``0`` — sucesso (persistência ok ou dry-run ok; conflitos/órfãos não-fatais ok)
- ``1`` — erro fatal pré-persistência ou de persistência:
  - args inválidos / ausentes
  - arquivo ausente ou ilegível / OOXML inválido
  - colunas obrigatórias ausentes
  - falha inesperada de persistência (``transaction.atomic`` faz rollback)
- Não há exit ``2`` nesta versão (args inválidos também → ``1``).

T010: CLI fino US1 (fase Notas + fórmula). T014: fase Comentários integrada
(não é mais stub); ``--dry-run`` stub até US3 via ``set_rollback`` no
importer. Sem UI/DRF/Celery; denylist intacta (não chama
stage/open/close/approval/``create_competency_lines``/adherence;
**não** edita ``evaluation.py``).
"""

from __future__ import annotations

import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.reviews.services.legacy_import import (
    LegacyParseError,
    LegacyPersistError,
    LegacySchemaError,
    format_notas_comentarios_report,
    import_notas_comentarios,
)


class Command(BaseCommand):
    """CLI fina T010+T014: notas → fórmula → comentários; dry-run/exit 0|1."""

    help = (
        'Importa notas por competência e comentários qualitativos do backup '
        'Sólides (OOXML) para o Greenn People. --avaliacoes reconstrói só o '
        'mapa de IDs colapsados (não reimporta cabeçalhos). Relatório inclui '
        'notas_*/comentarios_*/orfaos_*/conflitos_*.'
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
            '--notas',
            required=True,
            help='Path do backup de notas (OOXML real).',
        )
        parser.add_argument(
            '--comentarios',
            required=True,
            help='Path do backup de comentários (OOXML real).',
        )
        parser.add_argument(
            '--avaliacoes',
            required=True,
            help=(
                'Path do backup de cabeçalhos da 011. Só rebuild do mapa '
                'em memória; NÃO reimporta Avaliacao/Ciclo.'
            ),
        )
        parser.add_argument(
            '--habilidades',
            default=None,
            help=(
                'Path opcional do backup de habilidades. Só cria Competencia '
                'extra quando a nota referencia FK ausente no catálogo 003. '
                'NÃO importa matriz cargo↔competência.'
            ),
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
                'Parse + mapa + totais projetados sem commit no banco '
                '(stub até US3: rollback da mesma atomic).'
            ),
        )

    def handle(self, *args, **options) -> int:
        """Args → importer (notas → fórmula → comentários) → relatório mascarado.

        Persistência e ordem das fases ficam no importer (mesma
        ``transaction.atomic()``). Aqui só args, códigos de saída e emissão
        de ``format_notas_comentarios_report`` (inclui ``comentarios_*`` e
        ``orfaos_autor``). ``--avaliacoes`` nunca faz upsert de cabeçalho.
        """
        notas_path = options['notas']
        comentarios_path = options['comentarios']
        avaliacoes_path = options['avaliacoes']
        habilidades_path = options['habilidades']
        report_file = options['report_file']
        dry_run = options['dry_run']

        try:
            report = import_notas_comentarios(
                notas_path,
                comentarios_path,
                avaliacoes_path,
                habilidades_path=habilidades_path,
                dry_run=dry_run,
            )
        except LegacyParseError as exc:
            # Arquivo / OOXML / colunas — zero writes (parse pré-DB).
            raise CommandError(str(exc), returncode=1) from exc
        except LegacySchemaError as exc:
            # Pré-condição 003/010/011 ausente — zero writes (pré-atomic).
            raise CommandError(str(exc), returncode=1) from exc
        except LegacyPersistError as exc:
            # Exceção na persistência — atomic já fez rollback.
            raise CommandError(
                f'Falha na persistência: {exc}',
                returncode=1,
            ) from exc
        except CommandError:
            raise
        except Exception as exc:
            # Cinto e suspensório: qualquer outra falha → exit 1.
            raise CommandError(
                f'Falha na importação: {exc}',
                returncode=1,
            ) from exc

        self._emit_report(format_notas_comentarios_report(report), report_file)
        # Sucesso (persist ou dry-run, conflitos/órfãos não-fatais ok) → 0.
        return 0

    def _emit_report(self, text: str, report_file: str | None) -> None:
        """Stdout obrigatório; ``--report-file`` grava o mesmo texto UTF-8."""
        self.stdout.write(text, ending='')
        if report_file:
            Path(report_file).write_text(text, encoding='utf-8')
