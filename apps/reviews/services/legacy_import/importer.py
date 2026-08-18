"""Orquestração da importação de notas/comentários legado Sólides.

Superfície pública: ``import_notas_comentarios`` (reexportada por ``__init__``).
T002: stub — corpo em T009 (fase Notas) / T013 (fase Comentários) / T021
(``--dry-run`` + atomicidade das duas fases).

Ordem normativa (``contracts/import-command-contract.md``):
parse notas → parse comentários → mapa ``--avaliacoes`` (011, só memória) →
fase Notas → ``calcular_nota_final_*`` → fase Comentários, na mesma
``transaction.atomic()``.

Denylist intacta — **nunca** chama ``open_cycle`` / ``close_cycle`` /
``advance_stage`` / approval / ``create_competency_lines`` / adherence;
**nunca** edita ``evaluation.py``; **nunca** atribui ``etapa`` / ``concluida``.
"""

from __future__ import annotations

from pathlib import Path

from apps.accounts.services.legacy_import.report import ImportReport


class LegacySchemaError(Exception):
    """Pré-condição de schema ausente (003/010/011) — exit 1, zero writes.

    Esta fatia **não** gera migration. Falha de schema (ex. ``solides_id``
    ausente) não entra no ``atomic`` e não deixa escrita parcial.
    """


class LegacyPersistError(Exception):
    """Erro fatal durante persistência — ``atomic`` faz rollback; exit 1.

    Conflitos/órfãos não-fatais NÃO usam esta classe: vão para o relatório
    e exit ``0``.
    """


def import_notas_comentarios(
    notas_path: str | Path,
    comentarios_path: str | Path,
    avaliacoes_path: str | Path,
    *,
    habilidades_path: str | Path | None = None,
    dry_run: bool = False,
) -> ImportReport:
    """Orquestra parse → mapa → notas → fórmula → comentários (ou dry-run).

    Assinatura alinhada a ``contracts/import-command-contract.md``.

    ``--avaliacoes`` reconstrói o mapa de IDs colapsados em memória
    (IMPORTAR ``aggregate_avaliacao_headers``; **zero** upsert de cabeçalho).
    ``--habilidades`` é opcional (extras só como FK de nota, R11).

    Implementação: T009 / T013 / T021.
    """
    raise NotImplementedError(
        "T002 stub — implementar em T009 (notas), T013 (comentários), T021 (dry-run)"
    )
