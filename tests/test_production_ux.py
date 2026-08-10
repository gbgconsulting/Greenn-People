"""C7 / US6: health, artefatos de ops e contratos mínimos de UX."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
from django.template.loader import get_template
from django.test import Client
from django.urls import reverse

from apps.goals.models import Meta
from apps.goals.views import _proximo_passo_pos_reprovacao
from apps.reviews.models import Avaliacao

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.django_db
def test_health_ok_com_db():
    """C7 passo 1: GET /health/ → 200 com DB ok."""
    client = Client()
    response = client.get(reverse('health'))
    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'ok'
    assert payload['database'] == 'ok'


def test_backup_doc_aplicavel():
    """C7 passo 2: docs/ops/backup.md existe com mínimos obrigatórios."""
    path = REPO_ROOT / 'docs' / 'ops' / 'backup.md'
    assert path.is_file()
    text = path.read_text(encoding='utf-8')
    assert 'pg_dump' in text
    assert 'retenção' in text.lower() or 'Retenção' in text
    assert 'Frequência' in text or 'frequência' in text.lower()


@pytest.mark.django_db
def test_modal_template_a11y_contrato():
    """C7 passo 4: modal com role=dialog e aria-modal."""
    template = get_template('components/modal.html')
    html = template.render({'title': 'Teste'})
    assert 'role="dialog"' in html
    assert 'aria-modal="true"' in html


def test_modal_js_escape_e_restore():
    """C7 passo 4: JS mínimo com Escape e restore de foco."""
    js = (REPO_ROOT / 'static' / 'js' / 'modal.js').read_text(encoding='utf-8')
    assert "e.key !== 'Escape'" in js or "e.key === 'Escape'" in js
    assert 'lastTrigger' in js
    assert 'focus' in js


@pytest.mark.django_db
def test_empty_state_e_htmx_indicator_templates():
    """C7 passo 4: empty state + indicador HTMX renderizam."""
    empty = get_template('components/empty_state.html').render(
        {'message': 'Lista vazia', 'cta_label': 'Criar', 'cta_href': '/x/'},
    )
    assert 'Lista vazia' in empty
    assert 'Criar' in empty

    indicator = get_template('components/htmx_indicator.html').render({})
    assert 'id="htmx-indicator"' in indicator
    assert 'htmx-indicator' in indicator


@pytest.mark.django_db
def test_meta_row_ctas_pos_reprovacao_pt_br(meta, avaliacao):
    """T044: hints e rótulos de CTAs pós-reprovação em pt-BR."""
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_METAS
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    Meta.objects.filter(pk=meta.pk).update(status=Meta.Status.REPROVADA)
    meta.refresh_from_db()

    owner_ctx = _proximo_passo_pos_reprovacao(
        avaliacao,
        meta,
        is_owner=True,
        pode_progresso=False,
    )
    assert owner_ctx['item_reprovado'] is True
    assert owner_ctx['rotulo_editar'] == 'Corrigir'
    assert 'reenviar' in owner_ctx['proximo_passo_hint'].lower()

    manager_ctx = _proximo_passo_pos_reprovacao(
        avaliacao,
        meta,
        is_owner=False,
        pode_progresso=False,
    )
    assert manager_ctx['mostrar_link_editar'] is False
    assert 'aguardando' in manager_ctx['proximo_passo_hint'].lower()

    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_RESULTADOS
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    Meta.objects.filter(pk=meta.pk).update(
        status=Meta.Status.APROVADA,
        progresso=Decimal('50.00'),
        status_resultado=Meta.StatusResultado.REPROVADO,
    )
    meta.refresh_from_db()

    resultado_ctx = _proximo_passo_pos_reprovacao(
        avaliacao,
        meta,
        is_owner=True,
        pode_progresso=True,
    )
    assert resultado_ctx['rotulo_salvar_progresso'] == 'Corrigir e reenviar'
    assert 'corrigir e reenviar' in resultado_ctx['proximo_passo_hint'].lower()


@pytest.mark.django_db
def test_meta_form_usa_hint_do_helper_pos_reprovacao(meta, avaliacao, client):
    """T021: formulário de correção reutiliza copy de ``_proximo_passo_pos_reprovacao``."""
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_METAS
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    Meta.objects.filter(pk=meta.pk).update(status=Meta.Status.REPROVADA)
    meta.refresh_from_db()

    client.force_login(meta.usuario)
    response = client.get(reverse('goals:meta_update', kwargs={'pk': meta.pk}))
    assert response.status_code == 200
    body = response.content.decode()
    assert 'Corrigir meta' in body or '>Corrigir<' in body or 'Corrigir' in body
    assert 'Corrija a meta e salve para reenviar à aprovação.' in body
    assert 'Corrigir e reenviar' not in body
    assert 'Ajuste o conteúdo e salve' not in body


@pytest.mark.django_db
def test_meta_row_partial_renderiza_hint_pos_reprovacao(meta, avaliacao, rf):
    """T044: partial meta_row expõe hint visível após reprovação."""
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_METAS
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    Meta.objects.filter(pk=meta.pk).update(status=Meta.Status.REPROVADA)
    meta.refresh_from_db()

    request = rf.get('/')
    request.user = meta.usuario
    from apps.goals.views import _meta_row_context

    ctx = _meta_row_context(request, meta)
    html = get_template('goals/partials/meta_row.html').render(ctx, request=request)

    assert 'Corrigir' in html
    assert 'reenviar' in html.lower()


def test_modal_template_sem_fallback_ingles():
    """T044: fallback do modal não usa termo em inglês."""
    template = get_template('components/modal.html')
    html = template.render({})
    assert 'Dialog' not in html
    assert 'Formulário' in html
