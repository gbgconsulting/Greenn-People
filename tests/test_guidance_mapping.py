"""T006 — mapa etapa×papel e estados especiais de NextStepGuidance.

Asserts somente de DTO de apresentação (contracts/guidance-derivation.md).
Sem DB, sem mutators de stage/aprovação/fórmulas.
"""

from __future__ import annotations

import pytest

from apps.reviews.services.guidance import (
    ALLOWED_CTA_URL_NAMES,
    ETAPA_APROVACAO_METAS,
    ETAPA_APROVACAO_RESULTADOS,
    ETAPA_AVALIACAO,
    ETAPA_FEEDBACK,
    ETAPA_INPUT_METAS,
    ETAPA_RESULTADOS,
    STAGE_ORDER,
    resolve_next_step,
)

# (role, etapa, expected_title, expected_cta_url_name, expects_blocked_reason)
_MAPA_ETAPA_PAPEL: list[tuple[str, str, str, str | None, bool]] = [
    (
        'colaborador',
        ETAPA_INPUT_METAS,
        'Defina suas metas',
        'goals:meta_list',
        False,
    ),
    (
        'lider',
        ETAPA_INPUT_METAS,
        'Aguardando metas do time',
        'dashboard:team',
        True,
    ),
    (
        'colaborador',
        ETAPA_APROVACAO_METAS,
        'Metas em aprovação',
        'goals:meta_list',
        True,
    ),
    (
        'lider',
        ETAPA_APROVACAO_METAS,
        'Aprove as metas',
        'goals:meta_list',
        False,
    ),
    (
        'colaborador',
        ETAPA_RESULTADOS,
        'Atualize os resultados',
        'goals:meta_list',
        False,
    ),
    (
        'lider',
        ETAPA_RESULTADOS,
        'Aguardando resultados',
        'goals:meta_list',
        True,
    ),
    (
        'colaborador',
        ETAPA_APROVACAO_RESULTADOS,
        'Resultados em aprovação',
        'goals:meta_list',
        True,
    ),
    (
        'lider',
        ETAPA_APROVACAO_RESULTADOS,
        'Aprove os resultados',
        'goals:meta_list',
        False,
    ),
    (
        'colaborador',
        ETAPA_AVALIACAO,
        'Faça a autoavaliação',
        'reviews:self_assessment',
        False,
    ),
    (
        'lider',
        ETAPA_AVALIACAO,
        'Avalie o colaborador',
        'reviews:leader_assessment',
        False,
    ),
    (
        'colaborador',
        ETAPA_FEEDBACK,
        'Confirme ciência do feedback',
        'reviews:feedback_acknowledge',
        False,
    ),
    (
        'lider',
        ETAPA_FEEDBACK,
        'Registre o feedback',
        'reviews:feedback_create',
        False,
    ),
]


def _assert_dto_shape(g) -> None:
    assert isinstance(g.title, str) and g.title
    assert isinstance(g.body, str) and g.body
    assert isinstance(g.cta_kwargs, dict)
    if g.cta_url_name is None:
        assert g.cta_label is None
    else:
        assert g.cta_url_name in ALLOWED_CTA_URL_NAMES
        assert g.cta_label is not None


@pytest.mark.parametrize(
    'role,etapa,title,cta_url_name,expects_blocked',
    _MAPA_ETAPA_PAPEL,
    ids=[f'{r}-{e}' for r, e, *_ in _MAPA_ETAPA_PAPEL],
)
def test_mapa_etapa_papel_dto(
    role: str,
    etapa: str,
    title: str,
    cta_url_name: str | None,
    expects_blocked: bool,
):
    """Tabela canônica etapa×papel → título, CTA allowlisted e blocked_reason."""
    kwargs: dict = {'role': role, 'etapa': etapa, 'avaliacao_pk': 42}
    if role == 'colaborador' and etapa == ETAPA_FEEDBACK:
        kwargs['feedback_pk'] = 7

    g = resolve_next_step(**kwargs)

    _assert_dto_shape(g)
    assert g.title == title
    assert g.cta_url_name == cta_url_name
    if cta_url_name and cta_url_name.startswith('reviews:'):
        if cta_url_name == 'reviews:feedback_acknowledge':
            assert g.cta_kwargs == {'pk': 7}
        else:
            assert g.cta_kwargs.get('pk') == 42
    if expects_blocked:
        assert g.blocked_reason
    else:
        assert g.blocked_reason is None


@pytest.mark.parametrize('role', ['colaborador', 'lider', 'rh'])
def test_sem_ciclo_aberto_sem_cta_de_avanco(role: str):
    g = resolve_next_step(role=role, has_open_ciclo=False, etapa=ETAPA_INPUT_METAS)

    _assert_dto_shape(g)
    assert g.title == 'Sem ciclo em andamento'
    assert g.cta_url_name is None
    assert g.cta_label is None
    assert g.blocked_reason == 'Nenhum ciclo aberto.'


def test_vinculo_pendente_colaborador_cta_painel_opcional():
    g = resolve_next_step(
        role='colaborador',
        vinculo_pendente=True,
        etapa=ETAPA_INPUT_METAS,
    )

    _assert_dto_shape(g)
    assert g.title == 'Avaliação ainda não vinculada'
    assert g.cta_url_name == 'dashboard:personal'
    assert g.cta_label == 'Ver painel'
    assert g.blocked_reason == 'Vínculo ou avaliação ainda pendente.'


@pytest.mark.parametrize('role', ['lider', 'rh'])
def test_vinculo_pendente_nao_colaborador_sem_cta(role: str):
    g = resolve_next_step(
        role=role,
        vinculo_pendente=True,
        etapa=ETAPA_APROVACAO_METAS,
    )

    _assert_dto_shape(g)
    assert g.title == 'Avaliação ainda não vinculada'
    assert g.cta_url_name is None
    assert g.blocked_reason == 'Vínculo ou avaliação ainda pendente.'


def test_avaliacao_concluida_com_pk_cta_detail():
    g = resolve_next_step(
        role='colaborador',
        concluida=True,
        avaliacao_pk=99,
        etapa=ETAPA_FEEDBACK,
    )

    _assert_dto_shape(g)
    assert g.title == 'Ciclo concluído para você'
    assert g.cta_url_name == 'reviews:detail'
    assert g.cta_kwargs == {'pk': 99}
    assert g.blocked_reason is None


def test_avaliacao_concluida_sem_pk_sem_cta():
    g = resolve_next_step(role='lider', concluida=True, etapa=ETAPA_FEEDBACK)

    _assert_dto_shape(g)
    assert g.title == 'Ciclo concluído para você'
    assert g.cta_url_name is None
    assert g.blocked_reason == 'Avaliação concluída; sem próxima ação de etapa.'


def test_precedencia_sem_ciclo_sobre_vinculo_e_concluida():
    g = resolve_next_step(
        role='colaborador',
        has_open_ciclo=False,
        vinculo_pendente=True,
        concluida=True,
        etapa=ETAPA_INPUT_METAS,
    )
    assert g.title == 'Sem ciclo em andamento'
    assert g.cta_url_name is None


def test_precedencia_vinculo_sobre_concluida():
    g = resolve_next_step(
        role='colaborador',
        vinculo_pendente=True,
        concluida=True,
        avaliacao_pk=1,
        etapa=ETAPA_AVALIACAO,
    )
    assert g.title == 'Avaliação ainda não vinculada'
    assert g.cta_url_name == 'dashboard:personal'


def test_rh_acompanhamento_sem_cta_de_avanco():
    g = resolve_next_step(
        role='rh',
        etapa=ETAPA_APROVACAO_METAS,
        avaliacao_pk=5,
    )

    _assert_dto_shape(g)
    assert g.title == 'Acompanhe o ciclo'
    assert g.cta_url_name == 'reviews:detail'
    assert g.cta_kwargs == {'pk': 5}
    assert g.blocked_reason == 'Papel RH sem CTA de avanço de etapa.'


def test_feedback_colaborador_sem_feedback_pk_usa_lista():
    g = resolve_next_step(
        role='colaborador',
        etapa=ETAPA_FEEDBACK,
        avaliacao_pk=3,
    )

    _assert_dto_shape(g)
    assert g.title == 'Confirme ciência do feedback'
    assert g.cta_url_name == 'reviews:feedback_list'
    assert g.cta_kwargs == {'pk': 3}
    assert g.blocked_reason


def test_etapa_ausente_sem_cta():
    g = resolve_next_step(role='colaborador', etapa=None)

    _assert_dto_shape(g)
    assert g.title == 'Sem etapa atual'
    assert g.cta_url_name is None
    assert g.blocked_reason


def test_pos_reprovacao_metas_acionavel_sem_blocked():
    """T028 / FR-009: dono com meta reprovada → copy alinhada ao hint FR-007."""
    g = resolve_next_step(
        role='colaborador',
        etapa=ETAPA_APROVACAO_METAS,
        owner_correction_kind='metas',
    )

    _assert_dto_shape(g)
    assert g.title == 'Corrija a meta reprovada'
    assert g.body == 'Corrija a meta e salve para reenviar à aprovação.'
    assert g.cta_url_name == 'goals:meta_list'
    assert g.cta_label == 'Corrigir metas'
    assert g.blocked_reason is None


def test_pos_reprovacao_resultados_acionavel_sem_blocked():
    """T028 / FR-009: dono com resultado reprovado → mesmo destino e ação corretiva."""
    g = resolve_next_step(
        role='colaborador',
        etapa=ETAPA_APROVACAO_RESULTADOS,
        owner_correction_kind='resultados',
    )

    _assert_dto_shape(g)
    assert g.title == 'Corrija o resultado reprovado'
    assert g.body == 'Ajuste o progresso e clique em «Corrigir e reenviar».'
    assert g.cta_url_name == 'goals:meta_list'
    assert g.cta_label == 'Corrigir resultados'
    assert g.blocked_reason is None


def test_pos_reprovacao_nao_aplica_quando_concluida():
    """Estados especiais têm precedência sobre correção pós-reprovação."""
    g = resolve_next_step(
        role='colaborador',
        concluida=True,
        avaliacao_pk=1,
        etapa=ETAPA_APROVACAO_METAS,
        owner_correction_kind='metas',
    )
    assert g.title == 'Ciclo concluído para você'
    assert g.cta_url_name == 'reviews:detail'


def test_owner_correction_kind_invalido_levanta():
    with pytest.raises(ValueError, match='owner_correction_kind inválido'):
        resolve_next_step(
            role='colaborador',
            etapa=ETAPA_APROVACAO_METAS,
            owner_correction_kind='feedback',
        )


def test_role_invalido_levanta():
    with pytest.raises(ValueError, match='role inválido'):
        resolve_next_step(role='diretor', etapa=ETAPA_INPUT_METAS)


def test_ctas_mapeados_estao_na_allowlist():
    """Sanidade: nenhum destino do mapa sai da allowlist do contrato."""
    for role, etapa, _title, cta_url_name, _blocked in _MAPA_ETAPA_PAPEL:
        if cta_url_name is not None:
            assert cta_url_name in ALLOWED_CTA_URL_NAMES, (role, etapa, cta_url_name)
    assert set(STAGE_ORDER) == {
        ETAPA_INPUT_METAS,
        ETAPA_APROVACAO_METAS,
        ETAPA_RESULTADOS,
        ETAPA_APROVACAO_RESULTADOS,
        ETAPA_AVALIACAO,
        ETAPA_FEEDBACK,
    }
