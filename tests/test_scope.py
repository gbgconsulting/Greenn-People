"""T030: get_visible_users + IDOR em DetailView (ScopedObjectMixin → 404 + audit)."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.accounts.services.scope import get_scope_level, get_visible_users, user_in_scope
from apps.audit.models import AuditLog
from apps.reviews.models import Avaliacao
from tests.conftest import DEFAULT_PASSWORD


@pytest.fixture
def outsider(db, area, cargo_colab) -> CustomUser:
    """Usuário fora da hierarquia admin → líder → colaborador."""
    return CustomUser.objects.create_user(
        email='outsider@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Outsider Teste',
        cargo=cargo_colab,
        area=area,
        line_manager=None,
        email_confirmado_em=timezone.now(),
    )


@pytest.fixture
def gerente(db, admin, area, cargo_lider, cargo_colab) -> tuple[CustomUser, CustomUser, CustomUser]:
    """Hierarquia gerente → líder intermediário → folha (is_manager=True no topo)."""
    gerente_user = CustomUser.objects.create_user(
        email='gerente@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Gerente Teste',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    mid = CustomUser.objects.create_user(
        email='mid@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Líder Mid',
        cargo=cargo_lider,
        area=area,
        line_manager=gerente_user,
        email_confirmado_em=timezone.now(),
    )
    leaf = CustomUser.objects.create_user(
        email='leaf@test.greenn.com.br',
        password=DEFAULT_PASSWORD,
        nome='Colab Folha',
        cargo=cargo_colab,
        area=area,
        line_manager=mid,
        email_confirmado_em=timezone.now(),
    )
    return gerente_user, mid, leaf


# --- get_visible_users / user_in_scope / get_scope_level ---


@pytest.mark.django_db
def test_get_scope_level_por_papel(admin, lider, colaborador, gerente):
    gerente_user, _mid, _leaf = gerente
    assert get_scope_level(admin) == 'admin'
    assert get_scope_level(gerente_user) == 'manager'
    assert get_scope_level(lider) == 'leader'
    assert get_scope_level(colaborador) == 'collaborator'


@pytest.mark.django_db
def test_get_visible_users_admin_ve_todos(admin, lider, colaborador, outsider):
    visible = set(get_visible_users(admin).values_list('pk', flat=True))
    assert {admin.pk, lider.pk, colaborador.pk, outsider.pk}.issubset(visible)


@pytest.mark.django_db
def test_get_visible_users_leader_self_e_diretos(lider, colaborador, outsider, admin):
    visible = set(get_visible_users(lider).values_list('pk', flat=True))
    assert visible == {lider.pk, colaborador.pk}
    assert outsider.pk not in visible
    assert admin.pk not in visible
    assert user_in_scope(lider, colaborador.pk) is True
    assert user_in_scope(lider, outsider.pk) is False


@pytest.mark.django_db
def test_get_visible_users_collaborator_apenas_self(colaborador, lider, outsider):
    visible = set(get_visible_users(colaborador).values_list('pk', flat=True))
    assert visible == {colaborador.pk}
    assert user_in_scope(colaborador, lider.pk) is False
    assert user_in_scope(colaborador, outsider.pk) is False


@pytest.mark.django_db
def test_get_visible_users_manager_subarvore(gerente, outsider):
    gerente_user, mid, leaf = gerente
    visible = set(get_visible_users(gerente_user).values_list('pk', flat=True))
    assert visible == {gerente_user.pk, mid.pk, leaf.pk}
    assert outsider.pk not in visible
    assert user_in_scope(gerente_user, leaf.pk) is True
    assert user_in_scope(gerente_user, outsider.pk) is False


# --- ScopedObjectMixin / AvaliacaoDetailView IDOR ---


@pytest.mark.django_db
def test_detail_view_idor_fora_do_escopo_404_e_audit(
    ciclo_aberto,
    lider,
    outsider,
):
    """RF-36: registro existente fora do escopo → 404 + AuditLog ACCESS_DENIED."""
    av_out = Avaliacao.objects.create(ciclo=ciclo_aberto, usuario=outsider)
    client = Client()
    client.force_login(lider)
    url = reverse('reviews:detail', kwargs={'pk': av_out.pk})

    before = AuditLog.objects.filter(acao=AuditLog.Acao.ACCESS_DENIED).count()
    resp = client.get(url)
    after = AuditLog.objects.filter(acao=AuditLog.Acao.ACCESS_DENIED).count()

    assert resp.status_code == 404
    assert after == before + 1
    log = (
        AuditLog.objects.filter(acao=AuditLog.Acao.ACCESS_DENIED)
        .order_by('-created_at')
        .first()
    )
    assert log is not None
    assert log.usuario_id == lider.pk
    assert log.entity_type == 'reviews.Avaliacao'
    assert log.entity_id == av_out.pk


@pytest.mark.django_db
def test_detail_view_no_escopo_200(avaliacao, lider):
    client = Client()
    client.force_login(lider)
    url = reverse('reviews:detail', kwargs={'pk': avaliacao.pk})
    resp = client.get(url)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_detail_view_id_inexistente_404_sem_audit(lider):
    """ID inexistente → 404 genérico sem poluir auditoria (RF-36)."""
    client = Client()
    client.force_login(lider)
    url = reverse('reviews:detail', kwargs={'pk': 9_999_999})

    before = AuditLog.objects.filter(acao=AuditLog.Acao.ACCESS_DENIED).count()
    resp = client.get(url)
    after = AuditLog.objects.filter(acao=AuditLog.Acao.ACCESS_DENIED).count()

    assert resp.status_code == 404
    assert after == before
