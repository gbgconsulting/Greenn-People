"""T011/T019/T024/T025/T029/T031: AuthZ/IDOR da matriz interativa — escrita admin-only (SC-003).

Cobre serviços ``upsert_classification`` / ``toggle_classification_visibility``
e endpoints POST ``matrix_potencial`` / ``matrix_move`` / ``toggle_visibility``.

T024 (move): não-admin 403; payload potencial-only não muta desempenho;
snap coerente em ``(desempenho_derivado, P′)`` após POST admin.

T025 (drawer GET): gerente read-only sem controles de save/toggle; admin write;
POST direto de gerente continua 403 (FR-006/008).

T029 (escopo): queryset matriz / GET drawer via ``get_visible_users``;
gerente não vê fora do escopo; líder puro 403 na matriz (research R8).

T031 (SC-007): gate colaborador / ``visivel_ao_colaborador`` default False;
``/talent/mine/`` via ``get_visible_classification_for_collaborator`` sem vazamento;
fórmulas ``derive_desempenho`` / ``calculate_quadrante`` intactas.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.talent.models import ClassificacaoTalento
from apps.talent.services.classification import (
    calculate_quadrante,
    derive_desempenho,
    get_visible_classification_for_collaborator,
    toggle_classification_visibility,
    upsert_classification,
)
from tests.conftest import DEFAULT_PASSWORD


@pytest.fixture
def gerente(db, admin, area, cargo_lider, cargo_colab) -> tuple[CustomUser, CustomUser, CustomUser]:
    """Hierarquia gerente → líder intermediário → folha (``is_manager=True`` no topo)."""
    gerente_user = CustomUser.objects.create_user(
        email='gerente.matrix@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Gerente Matrix',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    mid = CustomUser.objects.create_user(
        email='mid.matrix@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Líder Mid Matrix',
        cargo=cargo_lider,
        area=area,
        line_manager=gerente_user,
        email_confirmado_em=timezone.now(),
    )
    leaf = CustomUser.objects.create_user(
        email='leaf.matrix@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Colab Folha Matrix',
        cargo=cargo_colab,
        area=area,
        line_manager=mid,
        email_confirmado_em=timezone.now(),
    )
    return gerente_user, mid, leaf


@pytest.fixture
def classificacao(ciclo_aberto, colaborador, avaliacao) -> ClassificacaoTalento:
    """Classificação existente com nota do líder (pré-condição de upsert)."""
    avaliacao.nota_final_lider = Decimal('0.50')
    avaliacao.save(update_fields=['nota_final_lider', 'updated_at'])
    return ClassificacaoTalento.objects.create(
        usuario=colaborador,
        ciclo=ciclo_aberto,
        desempenho=2,
        potencial=2,
        quadrante=ClassificacaoTalento.Quadrante.MEDIO_MEDIO,
        visivel_ao_colaborador=False,
    )


# --- Serviços: PermissionDenied + zero mutação ---


@pytest.mark.django_db
def test_upsert_classification_gerente_permission_denied(
    classificacao,
    colaborador,
    ciclo_aberto,
    gerente,
):
    """Gerente não pode persistir potencial via serviço (FR-006 / SC-003)."""
    gerente_user, _mid, _leaf = gerente
    assert gerente_user.is_manager
    assert not gerente_user.is_admin

    with pytest.raises(PermissionDenied):
        upsert_classification(
            usuario=colaborador,
            ciclo=ciclo_aberto,
            potencial=3,
            admin=gerente_user,
        )

    classificacao.refresh_from_db()
    assert classificacao.potencial == 2
    assert ClassificacaoTalento.objects.filter(
        usuario=colaborador,
        ciclo=ciclo_aberto,
    ).count() == 1


@pytest.mark.django_db
def test_upsert_classification_admin_ok(
    classificacao,
    colaborador,
    ciclo_aberto,
    admin,
):
    """Admin persiste potencial; desempenho/quadrante derivados."""
    result = upsert_classification(
        usuario=colaborador,
        ciclo=ciclo_aberto,
        potencial=3,
        admin=admin,
    )

    assert result.pk == classificacao.pk
    assert result.potencial == 3
    assert result.desempenho == 2
    assert result.quadrante == ClassificacaoTalento.Quadrante.MEDIO_ALTO


@pytest.mark.django_db
def test_toggle_classification_visibility_gerente_permission_denied(
    classificacao,
    gerente,
):
    """Gerente não pode alternar ``visivel_ao_colaborador`` via serviço."""
    gerente_user, _mid, _leaf = gerente

    with pytest.raises(PermissionDenied):
        toggle_classification_visibility(classificacao, gerente_user)

    classificacao.refresh_from_db()
    assert classificacao.visivel_ao_colaborador is False


@pytest.mark.django_db
def test_toggle_classification_visibility_admin_ok(classificacao, admin):
    """Admin inverte visibilidade sem alterar potencial/desempenho/quadrante."""
    before_potencial = classificacao.potencial
    before_desempenho = classificacao.desempenho
    before_quadrante = classificacao.quadrante

    result = toggle_classification_visibility(classificacao, admin)

    assert result.visivel_ao_colaborador is True
    assert result.potencial == before_potencial
    assert result.desempenho == before_desempenho
    assert result.quadrante == before_quadrante


# --- Endpoints HTTP: gerente forja POST → 403; admin passa AuthZ ---


@pytest.mark.django_db
def test_matrix_potencial_post_gerente_403(
    classificacao,
    colaborador,
    ciclo_aberto,
    gerente,
):
    """IDOR/forja: gerente POST potencial → 403; classificação intacta."""
    gerente_user, _mid, _leaf = gerente
    client = Client()
    client.force_login(gerente_user)

    resp = client.post(
        reverse('talent:matrix_potencial', kwargs={'user_pk': colaborador.pk}),
        data={'ciclo_id': ciclo_aberto.pk, 'potencial': 3},
    )

    assert resp.status_code == 403
    classificacao.refresh_from_db()
    assert classificacao.potencial == 2


@pytest.mark.django_db
def test_matrix_potencial_post_admin_htmx_ok(
    classificacao,
    colaborador,
    ciclo_aberto,
    admin,
):
    """Admin HTMX POST potencial → 200, persiste, drawer + OOB + toast."""
    client = Client()
    client.force_login(admin)

    resp = client.post(
        reverse('talent:matrix_potencial', kwargs={'user_pk': colaborador.pk}),
        data={'ciclo_id': ciclo_aberto.pk, 'potencial': 3},
        HTTP_HX_REQUEST='true',
    )

    assert resp.status_code == 200
    classificacao.refresh_from_db()
    assert classificacao.potencial == 3
    body = resp.content.decode()
    assert 'matrix-drawer-heading' in body or 'Potencial' in body
    assert 'hx-swap-oob' in body
    assert 'cell-2-2' in body  # origem
    assert 'cell-2-3' in body  # destino (desempenho 2, potencial 3)
    trigger = json.loads(resp['HX-Trigger'])
    assert trigger['showMessage']['level'] == 'success'
    assert 'Potencial atualizado' in trigger['showMessage']['message']


@pytest.mark.django_db
def test_matrix_potencial_post_admin_potencial_invalido_sem_mutacao(
    classificacao,
    colaborador,
    ciclo_aberto,
    admin,
):
    """Potencial inválido → erro PT-BR; classificação intacta (FR-005)."""
    client = Client()
    client.force_login(admin)

    resp = client.post(
        reverse('talent:matrix_potencial', kwargs={'user_pk': colaborador.pk}),
        data={'ciclo_id': ciclo_aberto.pk, 'potencial': 9},
        HTTP_HX_REQUEST='true',
    )

    assert resp.status_code == 200
    classificacao.refresh_from_db()
    assert classificacao.potencial == 2
    body = resp.content.decode()
    assert 'Potencial deve ser um inteiro entre 1 e 3.' in body
    assert 'hx-swap-oob' not in body
    trigger = json.loads(resp['HX-Trigger'])
    assert trigger['showMessage']['level'] == 'error'


@pytest.mark.django_db
def test_matrix_potencial_post_admin_nao_htmx_redirect(
    classificacao,
    colaborador,
    ciclo_aberto,
    admin,
):
    """Admin POST sem HTMX → redirect + potencial persistido."""
    client = Client()
    client.force_login(admin)

    resp = client.post(
        reverse('talent:matrix_potencial', kwargs={'user_pk': colaborador.pk}),
        data={'ciclo_id': ciclo_aberto.pk, 'potencial': 1},
    )

    assert resp.status_code == 302
    assert f'ciclo={ciclo_aberto.pk}' in resp['Location']
    classificacao.refresh_from_db()
    assert classificacao.potencial == 1


@pytest.mark.django_db
def test_toggle_visibility_post_gerente_403(classificacao, gerente):
    """Gerente POST toggle-visibility → 403; flag intacta."""
    gerente_user, _mid, _leaf = gerente
    client = Client()
    client.force_login(gerente_user)

    resp = client.post(
        reverse('talent:toggle_visibility', kwargs={'pk': classificacao.pk}),
    )

    assert resp.status_code == 403
    classificacao.refresh_from_db()
    assert classificacao.visivel_ao_colaborador is False


@pytest.mark.django_db
def test_toggle_visibility_post_admin_ok(classificacao, admin, ciclo_aberto):
    """Admin POST toggle-visibility → redirect + flag invertida."""
    client = Client()
    client.force_login(admin)

    resp = client.post(
        reverse('talent:toggle_visibility', kwargs={'pk': classificacao.pk}),
    )

    assert resp.status_code == 302
    assert f'ciclo={ciclo_aberto.pk}' in resp['Location']
    classificacao.refresh_from_db()
    assert classificacao.visivel_ao_colaborador is True


@pytest.mark.django_db
def test_toggle_visibility_post_admin_htmx_atualiza_drawer_e_card(
    classificacao,
    admin,
):
    """Admin HTMX toggle → drawer + célula OOB + toast; flag invertida."""
    client = Client()
    client.force_login(admin)
    assert classificacao.visivel_ao_colaborador is False

    resp = client.post(
        reverse('talent:toggle_visibility', kwargs={'pk': classificacao.pk}),
        HTTP_HX_REQUEST='true',
    )

    assert resp.status_code == 200
    classificacao.refresh_from_db()
    assert classificacao.visivel_ao_colaborador is True
    body = resp.content.decode()
    assert 'Visível' in body
    assert 'Ocultar' in body  # botão após liberar
    assert 'hx-swap-oob' in body
    assert f'cell-{classificacao.desempenho}-{classificacao.potencial}' in body
    trigger = json.loads(resp['HX-Trigger'])
    assert trigger['showMessage']['level'] == 'success'
    assert 'liberada' in trigger['showMessage']['message']


# --- POST matrix_move (T019 / T024 / drag-persist) ---


@pytest.mark.django_db
def test_matrix_move_post_gerente_403(
    classificacao,
    colaborador,
    ciclo_aberto,
    gerente,
):
    """T024: não-admin (gerente) POST move → 403; classificação intacta."""
    gerente_user, _mid, _leaf = gerente
    client = Client()
    client.force_login(gerente_user)

    resp = client.post(
        reverse('talent:matrix_move', kwargs={'user_pk': colaborador.pk}),
        data={
            'ciclo_id': ciclo_aberto.pk,
            'potencial': 3,
            'desempenho': 1,
        },
    )

    assert resp.status_code == 403
    classificacao.refresh_from_db()
    assert classificacao.potencial == 2
    assert classificacao.desempenho == 2


@pytest.mark.django_db
def test_matrix_move_post_admin_potencial_only_nao_muta_desempenho(
    classificacao,
    colaborador,
    ciclo_aberto,
    admin,
):
    """T024: payload potencial-only (sem desempenho) não pinta desempenho."""
    before_desempenho = classificacao.desempenho
    assert before_desempenho == 2

    client = Client()
    client.force_login(admin)

    resp = client.post(
        reverse('talent:matrix_move', kwargs={'user_pk': colaborador.pk}),
        data={
            'ciclo_id': ciclo_aberto.pk,
            'potencial': 1,
            # sem campo ``desempenho`` — contrato potencial-only
        },
        HTTP_HX_REQUEST='true',
    )

    assert resp.status_code == 200
    classificacao.refresh_from_db()
    assert classificacao.potencial == 1
    assert classificacao.desempenho == before_desempenho
    body = resp.content.decode()
    assert 'hx-swap-oob' in body
    assert 'cell-2-2' in body  # origem
    assert 'cell-2-1' in body  # destino snap (desempenho derivado, P′)
    trigger = json.loads(resp['HX-Trigger'])
    assert trigger['showMessage']['level'] == 'success'
    # Sem desempenho no payload → sem snap de linha → toast de sucesso padrão
    assert 'Só o potencial é alterado' not in trigger['showMessage']['message']
    assert 'Potencial atualizado' in trigger['showMessage']['message']


@pytest.mark.django_db
def test_matrix_move_post_admin_ignora_desempenho_e_snap_coerente(
    classificacao,
    colaborador,
    ciclo_aberto,
    admin,
):
    """T024: desempenho da célula-alvo ignorado; card em (D derivado, P′)."""
    client = Client()
    client.force_login(admin)

    resp = client.post(
        reverse('talent:matrix_move', kwargs={'user_pk': colaborador.pk}),
        data={
            'ciclo_id': ciclo_aberto.pk,
            'potencial': 3,
            'desempenho': 1,  # incompatível — servidor ignora para mutação
        },
        HTTP_HX_REQUEST='true',
    )

    assert resp.status_code == 200
    classificacao.refresh_from_db()
    assert classificacao.potencial == 3
    assert classificacao.desempenho == 2  # derivado, não pintado
    body = resp.content.decode()
    assert 'hx-swap-oob' in body
    assert 'cell-2-2' in body  # origem
    assert 'cell-2-3' in body  # snap (desempenho 2, potencial 3)
    assert 'cell-1-3' not in body  # nunca posiciona na linha pintada
    trigger = json.loads(resp['HX-Trigger'])
    assert trigger['showMessage']['level'] == 'success'
    assert 'Só o potencial é alterado' in trigger['showMessage']['message']


@pytest.mark.django_db
def test_matrix_move_post_admin_noop_potencial_inalterado(
    classificacao,
    colaborador,
    ciclo_aberto,
    admin,
):
    """Mesmo potencial → noop (200, sem OOB, sem mutação material)."""
    client = Client()
    client.force_login(admin)

    resp = client.post(
        reverse('talent:matrix_move', kwargs={'user_pk': colaborador.pk}),
        data={'ciclo_id': ciclo_aberto.pk, 'potencial': 2},
        HTTP_HX_REQUEST='true',
    )

    assert resp.status_code == 200
    assert 'hx-swap-oob' not in resp.content.decode()
    classificacao.refresh_from_db()
    assert classificacao.potencial == 2
    trigger = json.loads(resp['HX-Trigger'])
    assert 'inalterado' in trigger['showMessage']['message'].lower()


@pytest.mark.django_db
def test_matrix_move_post_potencial_invalido_400(
    classificacao,
    colaborador,
    ciclo_aberto,
    admin,
):
    """Potencial inválido → 400 + toast erro; zero mutação."""
    client = Client()
    client.force_login(admin)

    resp = client.post(
        reverse('talent:matrix_move', kwargs={'user_pk': colaborador.pk}),
        data={'ciclo_id': ciclo_aberto.pk, 'potencial': 9},
        HTTP_HX_REQUEST='true',
    )

    assert resp.status_code == 400
    classificacao.refresh_from_db()
    assert classificacao.potencial == 2
    trigger = json.loads(resp['HX-Trigger'])
    assert trigger['showMessage']['level'] == 'error'


# --- T025: GET drawer write (admin) vs read-only (gerente) ---


@pytest.mark.django_db
def test_matrix_drawer_get_admin_write_controls(
    classificacao,
    colaborador,
    ciclo_aberto,
    admin,
):
    """Admin HTMX GET drawer → modo write com Salvar/toggle e fallback classify."""
    client = Client()
    client.force_login(admin)

    resp = client.get(
        reverse('talent:matrix_drawer', kwargs={'user_pk': colaborador.pk}),
        data={'ciclo': ciclo_aberto.pk},
        HTTP_HX_REQUEST='true',
    )

    assert resp.status_code == 200
    body = resp.content.decode()
    assert 'data-drawer-mode="write"' in body
    assert 'data-drawer-writable="true"' in body
    assert 'data-drawer-potencial-form' in body
    assert 'data-drawer-visibility-form' in body
    assert 'Salvar' in body
    assert 'Liberar' in body or 'Ocultar' in body
    assert 'data-drawer-classify-fallback' in body
    assert 'text-emerald-700 underline' not in body
    assert 'data-drawer-close' in body
    assert 'data-drawer-potencial-readonly' not in body
    assert 'data-drawer-readonly-hint' not in body


@pytest.mark.django_db
def test_matrix_drawer_get_gerente_readonly_sem_controles(
    ciclo_aberto,
    gerente,
):
    """Gerente HTMX GET drawer no escopo → read-only; sem save/toggle/classify."""
    gerente_user, _mid, leaf = gerente
    ClassificacaoTalento.objects.create(
        usuario=leaf,
        ciclo=ciclo_aberto,
        desempenho=2,
        potencial=3,
        quadrante=ClassificacaoTalento.Quadrante.MEDIO_ALTO,
        visivel_ao_colaborador=False,
    )

    client = Client()
    client.force_login(gerente_user)

    resp = client.get(
        reverse('talent:matrix_drawer', kwargs={'user_pk': leaf.pk}),
        data={'ciclo': ciclo_aberto.pk},
        HTTP_HX_REQUEST='true',
    )

    assert resp.status_code == 200
    body = resp.content.decode()
    assert 'data-drawer-mode="read"' in body
    assert 'data-drawer-writable="false"' in body
    assert 'aria-readonly="true"' in body
    assert 'data-drawer-readonly-hint' in body
    assert 'data-drawer-potencial-readonly' in body
    assert 'Alto' in body  # potencial_label
    assert leaf.nome in body or leaf.email in body
    assert 'data-drawer-potencial-form' not in body
    assert 'data-drawer-visibility-form' not in body
    assert 'data-drawer-classify-fallback' not in body
    assert 'name="potencial"' not in body
    assert '>Salvar<' not in body
    assert '>Liberar<' not in body
    assert '>Ocultar<' not in body


# --- T029: escopo get_visible_users + líder puro 403 (authz-scope / R8) ---


@pytest.mark.django_db
def test_matrix_get_lider_puro_403(lider, colaborador):
    """T029 / R8: líder puro (is_leader, not is_manager) → 403 na matriz."""
    assert lider.is_leader
    assert not lider.is_manager
    assert not lider.is_admin
    # colaborador garante hierarquia de liderados diretos
    assert colaborador.line_manager_id == lider.pk

    client = Client()
    client.force_login(lider)
    resp = client.get(reverse('talent:matrix'))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_matrix_drawer_get_lider_puro_403(lider, colaborador, classificacao, ciclo_aberto):
    """T029 / R8: líder puro também é barrado no GET drawer (mesmo mixin)."""
    assert lider.is_leader
    assert not lider.is_manager

    client = Client()
    client.force_login(lider)
    resp = client.get(
        reverse('talent:matrix_drawer', kwargs={'user_pk': colaborador.pk}),
        data={'ciclo': ciclo_aberto.pk},
        HTTP_HX_REQUEST='true',
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_matrix_get_gerente_nao_ve_fora_do_escopo(
    ciclo_aberto,
    gerente,
    classificacao,
    colaborador,
    area,
    cargo_colab,
):
    """T029: grade só lista ``usuario__in=get_visible_users``; outsider oculto."""
    from apps.talent.views import _matrix_classificacoes_qs

    gerente_user, _mid, leaf = gerente
    ClassificacaoTalento.objects.create(
        usuario=leaf,
        ciclo=ciclo_aberto,
        desempenho=1,
        potencial=1,
        quadrante=ClassificacaoTalento.Quadrante.BAIXO_BAIXO,
        visivel_ao_colaborador=False,
    )
    outsider = CustomUser.objects.create_user(
        email='outsider.matrix@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Outsider Matrix Escopo',
        cargo=cargo_colab,
        area=area,
        line_manager=None,
        email_confirmado_em=timezone.now(),
    )
    ClassificacaoTalento.objects.create(
        usuario=outsider,
        ciclo=ciclo_aberto,
        desempenho=3,
        potencial=3,
        quadrante=ClassificacaoTalento.Quadrante.ALTO_ALTO,
        visivel_ao_colaborador=False,
    )

    qs = _matrix_classificacoes_qs(gerente_user, ciclo_aberto)
    visible_user_pks = set(qs.values_list('usuario_id', flat=True))
    assert leaf.pk in visible_user_pks
    assert outsider.pk not in visible_user_pks
    assert colaborador.pk not in visible_user_pks  # sob outro ramo (lider/admin)

    client = Client()
    client.force_login(gerente_user)
    resp = client.get(reverse('talent:matrix'), data={'ciclo': ciclo_aberto.pk})
    assert resp.status_code == 200
    body = resp.content.decode()
    assert leaf.email in body or leaf.nome in body
    assert outsider.email not in body
    assert 'Outsider Matrix Escopo' not in body
    assert colaborador.email not in body


@pytest.mark.django_db
def test_matrix_drawer_get_gerente_fora_do_escopo_404(
    ciclo_aberto,
    gerente,
    classificacao,
    colaborador,
):
    """T029: drawer GET com pessoa fora do escopo → 404 (sem vazar existência)."""
    gerente_user, _mid, _leaf = gerente
    # ``classificacao`` pertence a ``colaborador`` (ramo admin→lider), fora do gerente
    assert colaborador.pk != _leaf.pk

    client = Client()
    client.force_login(gerente_user)
    resp = client.get(
        reverse('talent:matrix_drawer', kwargs={'user_pk': colaborador.pk}),
        data={'ciclo': ciclo_aberto.pk},
        HTTP_HX_REQUEST='true',
    )
    assert resp.status_code == 404


# --- T031: gate colaborador + fórmulas intactas (SC-007 / FR-009) ---


@pytest.mark.django_db
def test_visivel_ao_colaborador_default_false_no_model_e_upsert(
    classificacao,
    colaborador,
    ciclo_aberto,
    admin,
    avaliacao,
):
    """T031: default restritivo; upsert não libera visibilidade por padrão."""
    field = ClassificacaoTalento._meta.get_field('visivel_ao_colaborador')
    assert field.default is False
    assert classificacao.visivel_ao_colaborador is False

    # Remove classificação pré-existente e recria via upsert (caminho create)
    ClassificacaoTalento.objects.filter(
        usuario=colaborador,
        ciclo=ciclo_aberto,
    ).delete()
    avaliacao.nota_final_lider = Decimal('0.50')
    avaliacao.save(update_fields=['nota_final_lider', 'updated_at'])

    created = upsert_classification(
        usuario=colaborador,
        ciclo=ciclo_aberto,
        potencial=2,
        admin=admin,
    )
    assert created.visivel_ao_colaborador is False


@pytest.mark.django_db
def test_get_visible_classification_respeita_flag(
    classificacao,
    colaborador,
    ciclo_aberto,
):
    """T031: serviço de mine só retorna registro quando liberado."""
    assert classificacao.visivel_ao_colaborador is False
    assert (
        get_visible_classification_for_collaborator(
            colaborador,
            ciclo=ciclo_aberto,
        )
        is None
    )

    classificacao.visivel_ao_colaborador = True
    classificacao.save(update_fields=['visivel_ao_colaborador', 'updated_at'])
    visible = get_visible_classification_for_collaborator(
        colaborador,
        ciclo=ciclo_aberto,
    )
    assert visible is not None
    assert visible.pk == classificacao.pk


@pytest.mark.django_db
def test_talent_mine_oculto_nao_vaza_ninebox(
    classificacao,
    colaborador,
    ciclo_aberto,
):
    """T031: ``/talent/mine/`` sem vazamento de desempenho/potencial/quadrante."""
    assert classificacao.visivel_ao_colaborador is False

    client = Client()
    client.force_login(colaborador)
    resp = client.get(
        reverse('talent:mine'),
        data={'ciclo': ciclo_aberto.pk},
    )
    assert resp.status_code == 200
    assert resp.context['classificacao'] is None
    assert resp.context['classificacao_oculta'] is True

    body = resp.content.decode().lower()
    assert 'não liberada' in body or 'nao liberada' in body or 'ainda não liberou' in body
    # Sem cards de resultado (template só os renderiza se ``classificacao``)
    assert 'resultado da classificação' not in body
    assert 'matriz 9-box' not in body
    assert 'nível 2 de 3' not in body
    assert 'nivel 2 de 3' not in body


@pytest.mark.django_db
def test_talent_mine_liberado_mostra_classificacao(
    classificacao,
    colaborador,
    ciclo_aberto,
):
    """T031: após liberação, mine mostra 9-box do próprio colaborador."""
    classificacao.visivel_ao_colaborador = True
    classificacao.save(update_fields=['visivel_ao_colaborador', 'updated_at'])

    client = Client()
    client.force_login(colaborador)
    resp = client.get(
        reverse('talent:mine'),
        data={'ciclo': ciclo_aberto.pk},
    )
    assert resp.status_code == 200
    assert resp.context['classificacao'] is not None
    body = resp.content.decode().lower()
    assert 'nível 2 de 3' in body or 'nivel 2 de 3' in body
    assert 'matriz 9-box' in body


@pytest.mark.django_db
def test_matrix_surface_t020_freeze_markers(
    classificacao,
    admin,
    ciclo_aberto,
):
    """T020 [US2]: matriz consome Freeze (table-frame, empty_state, min-w-0; sem cap B1)."""
    client = Client()
    client.force_login(admin)

    resp = client.get(reverse('talent:matrix'), data={'ciclo': ciclo_aberto.pk})
    assert resp.status_code == 200
    body = resp.content.decode()
    assert 'ninebox-matrix' in body or 'ninebox-matrix-empty' in body
    assert 'table-frame' in body
    assert 'empty_state.html' not in body  # include renderizado, não path
    assert 'components/empty_state' not in body
    assert 'max-w-5xl' not in body
    assert 'max-w-6xl' not in body
    assert 'min-w-0' in body
    assert 'badge_status' not in body  # include renderizado
    assert 'Visível' in body or 'Oculto' in body or 'classificado' in body


@pytest.mark.django_db
def test_colaborador_sem_acesso_util_a_matriz(colaborador):
    """T031: colaborador puro não usa a matriz (RequiresManagerOrAdmin)."""
    client = Client()
    client.force_login(colaborador)
    resp = client.get(reverse('talent:matrix'))
    assert resp.status_code == 403


def test_derive_desempenho_limites_contrato():
    """T031: limiares 0.33 / 0.66 intactos (calculation-contract / SC-007)."""
    assert derive_desempenho(Decimal('0.00')) == 1
    assert derive_desempenho(Decimal('0.32')) == 1
    assert derive_desempenho(Decimal('0.33')) == 2
    assert derive_desempenho(Decimal('0.50')) == 2
    assert derive_desempenho(Decimal('0.66')) == 2
    assert derive_desempenho(Decimal('0.67')) == 3
    assert derive_desempenho(Decimal('1.00')) == 3


def test_calculate_quadrante_tabela_9_box():
    """T031: rótulos desempenho_potencial intactos (calculation-contract)."""
    esperado = {
        (1, 1): 'baixo_baixo',
        (1, 2): 'baixo_medio',
        (1, 3): 'baixo_alto',
        (2, 1): 'medio_baixo',
        (2, 2): 'medio_medio',
        (2, 3): 'medio_alto',
        (3, 1): 'alto_baixo',
        (3, 2): 'alto_medio',
        (3, 3): 'alto_alto',
    }
    for (desempenho, potencial), label in esperado.items():
        assert calculate_quadrante(desempenho, potencial) == label
