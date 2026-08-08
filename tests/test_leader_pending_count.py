"""T018 — soma N+M+K e exclusão fora do escopo do LeaderPendingBadge.

Asserts só de DTO de apresentação (contracts/leader-pending-badge.md).
Reusa predicados existentes; sem mutators de stage/aprovação/AuthZ.
"""

from __future__ import annotations

import pytest
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.services.cycle import close_cycle
from apps.goals.models import Meta
from apps.reviews.models import Avaliacao, Feedback
from apps.reviews.services.pending_counts import (
    LeaderPendingBadge,
    resolve_leader_pending_badge,
)
from tests.conftest import DEFAULT_PASSWORD


def _set_etapa(avaliacao: Avaliacao, etapa: str) -> Avaliacao:
    avaliacao.etapa = etapa
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    return avaliacao


def _make_colab(*, email: str, lider, area, cargo) -> CustomUser:
    return CustomUser.objects.create_user(
        email=email,
        password=DEFAULT_PASSWORD,
        nome=email.split('@')[0],
        cargo=cargo,
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )


def _avaliacao_for(ciclo, usuario, etapa: str) -> Avaliacao:
    av, _ = Avaliacao.objects.get_or_create(ciclo=ciclo, usuario=usuario)
    return _set_etapa(av, etapa)


# --- DTO (sem DB) ---


def test_dto_total_igual_soma_das_parcelas():
    badge = LeaderPendingBadge(total=6, aprovacoes=2, avaliacoes=3, feedbacks=1)
    assert badge.total == badge.aprovacoes + badge.avaliacoes + badge.feedbacks


def test_dto_total_divergente_levanta():
    with pytest.raises(ValueError, match='total deve ser'):
        LeaderPendingBadge(total=9, aprovacoes=1, avaliacoes=1, feedbacks=1)


def test_dto_contagens_negativas_levantam():
    with pytest.raises(ValueError, match='>= 0'):
        LeaderPendingBadge(total=-1, aprovacoes=0, avaliacoes=0, feedbacks=-1)


def test_resolve_leader_sem_pk_retorna_zero():
    class _Anon:
        pk = None

    badge = resolve_leader_pending_badge(_Anon())
    assert badge == LeaderPendingBadge(
        total=0, aprovacoes=0, avaliacoes=0, feedbacks=0
    )


# --- Integração: soma N+M+K + escopo ---


@pytest.mark.django_db
def test_soma_n_mais_m_mais_k_elegiveis(
    lider,
    colaborador,
    ciclo_aberto,
    objetivo,
    area,
    cargo_colab,
):
    """Líder com N=2 aprovações + M=1 avaliação + K=1 feedback ⇒ total == N+M+K."""
    av_aprov = Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador)
    _set_etapa(av_aprov, Avaliacao.Etapa.APROVACAO_METAS)
    Meta.objects.create(
        usuario=colaborador,
        objetivo_estrategico=objetivo,
        descricao='Meta aprovável A',
        status=Meta.Status.PENDENTE,
    )
    Meta.objects.create(
        usuario=colaborador,
        objetivo_estrategico=objetivo,
        descricao='Meta aprovável B',
        status=Meta.Status.PENDENTE,
    )

    colab_aval = _make_colab(
        email='colab-aval@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo=cargo_colab,
    )
    _avaliacao_for(ciclo_aberto, colab_aval, Avaliacao.Etapa.AVALIACAO)

    colab_fb = _make_colab(
        email='colab-fb@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo=cargo_colab,
    )
    _avaliacao_for(ciclo_aberto, colab_fb, Avaliacao.Etapa.FEEDBACK)

    badge = resolve_leader_pending_badge(lider)

    assert badge.aprovacoes == 2
    assert badge.avaliacoes == 1
    assert badge.feedbacks == 1
    assert badge.total == 2 + 1 + 1


@pytest.mark.django_db
def test_usuario_fora_do_escopo_nao_entra_na_soma(
    lider,
    colaborador,
    ciclo_aberto,
    objetivo,
    area,
    cargo_colab,
):
    """Pendências de outsider (fora de get_visible_users) não somam no badge."""
    av_in = Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador)
    _set_etapa(av_in, Avaliacao.Etapa.APROVACAO_METAS)
    Meta.objects.create(
        usuario=colaborador,
        objetivo_estrategico=objetivo,
        descricao='Meta no escopo',
        status=Meta.Status.PENDENTE,
    )

    outsider = CustomUser.objects.create_user(
        email='outsider-badge@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Outsider Badge',
        cargo=cargo_colab,
        area=area,
        line_manager=None,
        email_confirmado_em=timezone.now(),
    )
    av_out = Avaliacao.objects.create(
        ciclo=ciclo_aberto,
        usuario=outsider,
        etapa=Avaliacao.Etapa.APROVACAO_METAS,
    )
    Meta.objects.create(
        usuario=outsider,
        objetivo_estrategico=objetivo,
        descricao='Meta fora do escopo',
        status=Meta.Status.PENDENTE,
    )
    # Espalhar outras fontes “elegíveis” no outsider — ainda devem ser ignoradas.
    colab_out_aval = CustomUser.objects.create_user(
        email='outsider-aval@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Outsider Aval',
        cargo=cargo_colab,
        area=area,
        line_manager=outsider,
        email_confirmado_em=timezone.now(),
    )
    Avaliacao.objects.create(
        ciclo=ciclo_aberto,
        usuario=colab_out_aval,
        etapa=Avaliacao.Etapa.AVALIACAO,
    )
    Avaliacao.objects.create(
        ciclo=ciclo_aberto,
        usuario=CustomUser.objects.create_user(
            email='outsider-fb@test.greenn.com.br',
            password=DEFAULT_PASSWORD,
            nome='Outsider FB',
            cargo=cargo_colab,
            area=area,
            line_manager=outsider,
            email_confirmado_em=timezone.now(),
        ),
        etapa=Avaliacao.Etapa.FEEDBACK,
    )

    badge = resolve_leader_pending_badge(lider)

    assert badge.aprovacoes == 1
    assert badge.avaliacoes == 0
    assert badge.feedbacks == 0
    assert badge.total == 1
    assert av_out.usuario_id not in {
        colaborador.pk,
        lider.pk,
    }


@pytest.mark.django_db
def test_sem_ciclo_aberto_badge_zero(lider, ciclo_aberto):
    close_cycle(ciclo_aberto)
    badge = resolve_leader_pending_badge(lider)
    assert badge.total == 0
    assert badge.aprovacoes == badge.avaliacoes == badge.feedbacks == 0


@pytest.mark.django_db
def test_meta_ja_aprovada_nao_conta_como_aprovacao(
    lider,
    colaborador,
    ciclo_aberto,
    objetivo,
):
    av = Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador)
    _set_etapa(av, Avaliacao.Etapa.APROVACAO_METAS)
    Meta.objects.create(
        usuario=colaborador,
        objetivo_estrategico=objetivo,
        descricao='Já aprovada',
        status=Meta.Status.APROVADA,
    )
    Meta.objects.create(
        usuario=colaborador,
        objetivo_estrategico=objetivo,
        descricao='Ainda pendente',
        status=Meta.Status.PENDENTE,
    )

    badge = resolve_leader_pending_badge(lider)
    assert badge.aprovacoes == 1
    assert badge.total == 1


@pytest.mark.django_db
def test_feedback_lider_ja_existente_nao_conta(
    lider,
    colaborador,
    ciclo_aberto,
):
    av = Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador)
    _set_etapa(av, Avaliacao.Etapa.FEEDBACK)
    Feedback.objects.create(
        avaliacao=av,
        autor=lider,
        tipo=Feedback.Tipo.LIDER,
        conteudo='Já registrado',
    )

    badge = resolve_leader_pending_badge(lider)
    assert badge.feedbacks == 0
    assert badge.total == 0


@pytest.mark.django_db
def test_avaliacao_propria_do_lider_nao_entra_em_feedbacks(
    lider,
    ciclo_aberto,
):
    """Badge não conta a avaliação do próprio líder (ação de colaborador)."""
    av_lider = Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=lider)
    _set_etapa(av_lider, Avaliacao.Etapa.FEEDBACK)

    badge = resolve_leader_pending_badge(lider)
    assert badge.feedbacks == 0
    assert badge.total == 0


@pytest.mark.django_db
def test_etapa_errada_nao_infla_contagem(
    lider,
    colaborador,
    ciclo_aberto,
    objetivo,
    area,
    cargo_colab,
):
    """Etapa input_metas / resultados não vira aprovação, avaliação ou feedback."""
    av = Avaliacao.objects.get(ciclo=ciclo_aberto, usuario=colaborador)
    _set_etapa(av, Avaliacao.Etapa.INPUT_METAS)
    Meta.objects.create(
        usuario=colaborador,
        objetivo_estrategico=objetivo,
        descricao='Meta em input',
        status=Meta.Status.PENDENTE,
    )
    colab2 = _make_colab(
        email='colab-resultados@test.greenn.com.br',
        lider=lider,
        area=area,
        cargo=cargo_colab,
    )
    _avaliacao_for(ciclo_aberto, colab2, Avaliacao.Etapa.RESULTADOS)

    badge = resolve_leader_pending_badge(lider)
    assert badge.total == 0


# --- T019: context processor (exposição na nav) ---


@pytest.mark.django_db
def test_processor_anonimo_badge_zero(rf):
    from django.contrib.auth.models import AnonymousUser

    from apps.core.context_processors import (
        leader_pending_badge as leader_pending_badge_processor,
    )

    request = rf.get('/')
    request.user = AnonymousUser()

    ctx = leader_pending_badge_processor(request)

    assert ctx['leader_pending_badge'] == LeaderPendingBadge(
        total=0, aprovacoes=0, avaliacoes=0, feedbacks=0
    )


@pytest.mark.django_db
def test_processor_expõe_total_do_resolve(lider, rf):
    from apps.core.context_processors import (
        leader_pending_badge as leader_pending_badge_processor,
    )

    request = rf.get('/')
    request.user = lider

    ctx = leader_pending_badge_processor(request)
    expected = resolve_leader_pending_badge(lider)

    assert ctx['leader_pending_badge'] == expected
