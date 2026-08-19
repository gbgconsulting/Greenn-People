"""Validação quickstart C1–C7 — hardening pós-MVP (T042).

Executa os cenários de specs/002-pos-mvp-hardening/quickstart.md em
transação com rollback (não persiste dados de teste).

Uso:
  export DJANGO_SETTINGS_MODULE=config.settings.dev
  python scripts/validate_quickstart_c1_c7.py
"""

from __future__ import annotations

import os
import sys
import traceback
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

import django

django.setup()

from django.conf import settings

if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + [
        'testserver',
        'localhost',
    ]

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.accounts.services.offboarding import reassign_direct_reports
from apps.audit.context import audit_actor
from apps.audit.models import AuditLog
from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.cycles.models import Ciclo
from apps.cycles.services.cycle import close_cycle, open_cycle
from apps.cycles.services.stage import can_advance
from apps.goals.models import Meta, ObjetivoEstrategico
from apps.goals.services.approval import (
    approve_meta,
    approve_resultado,
    reject_meta,
    reject_resultado,
)
from apps.notifications.tasks import enviar_lembrete_prazo_etapa
from apps.organization.models import Area, Cargo
from apps.pdi.models import AcaoPDI, PDI
from apps.reviews.models import Avaliacao
from apps.reviews.services.enrollment import ensure_avaliacao_for_user

REPO_ROOT = Path(__file__).resolve().parents[1]
PASSWORD = 'ValidateC1C7!'


class ScenarioError(AssertionError):
    pass


def _ok(name: str) -> None:
    print(f'  ✓ {name}')


def _fail(name: str, exc: BaseException) -> None:
    print(f'  ✗ {name}: {exc}')


def _unique(prefix: str) -> str:
    stamp = timezone.now().strftime('%Y%m%d%H%M%S%f')
    return f'{prefix}-{stamp}'


def _ensure_no_open_cycle() -> None:
    for ciclo in Ciclo.objects.filter(status=Ciclo.Status.ABERTO):
        close_cycle(ciclo)


def _make_users():
    area = Area.objects.create(nome=_unique('Área'))
    cargo_lider = Cargo.objects.create(nome=_unique('Líder'), nivel=2)
    cargo_colab = Cargo.objects.create(nome=_unique('Analista'), nivel=1)
    admin = CustomUser.objects.create_user(
        email=f'{_unique("admin")}@test.local',
        password=PASSWORD,
        nome='Admin C1C7',
        is_admin=True,
        is_staff=True,
        email_confirmado_em=timezone.now(),
    )
    lider = CustomUser.objects.create_user(
        email=f'{_unique("lider")}@test.local',
        password=PASSWORD,
        nome='Líder C1C7',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    colab = CustomUser.objects.create_user(
        email=f'{_unique("colab")}@test.local',
        password=PASSWORD,
        nome='Colab C1C7',
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )
    return area, cargo_lider, cargo_colab, admin, lider, colab


def scenario_c1(admin, lider, colab):
    print('C1 — Pós-reprovação de meta')
    _ensure_no_open_cycle()
    today = timezone.localdate()
    ciclo = Ciclo.objects.create(
        nome=_unique('Ciclo C1'),
        data_inicio=today - timedelta(days=10),
        data_fim=today + timedelta(days=20),
        status=Ciclo.Status.ENCERRADO,
    )
    open_cycle(ciclo)
    avaliacao = Avaliacao.objects.get(ciclo=ciclo, usuario=colab)
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_METAS
    avaliacao.save(update_fields=['etapa', 'updated_at'])

    objetivo = ObjetivoEstrategico.objects.create(
        descricao='Obj C1',
        ciclo=ciclo,
    )
    meta_a = Meta.objects.create(
        usuario=colab,
        objetivo_estrategico=objetivo,
        descricao='Meta A',
        status=Meta.Status.PENDENTE,
    )
    meta_b = Meta.objects.create(
        usuario=colab,
        objetivo_estrategico=objetivo,
        descricao='Meta B',
        status=Meta.Status.APROVADA,
    )
    etapa_antes = avaliacao.etapa

    with audit_actor(lider):
        reject_meta(meta_a, lider)
    meta_a.refresh_from_db()
    avaliacao.refresh_from_db()
    meta_b.refresh_from_db()
    if meta_a.status != Meta.Status.REPROVADA:
        raise ScenarioError(f'status esperado reprovada, got {meta_a.status}')
    if avaliacao.etapa != etapa_antes:
        raise ScenarioError('etapa retrocedeu após reject')
    if meta_b.status != Meta.Status.APROVADA:
        raise ScenarioError('irmão aprovado foi alterado')
    _ok('reject mantém etapa e irmão')

    meta_a.descricao = 'Meta A corrigida'
    meta_a.reopen()
    meta_a.save()
    meta_a.refresh_from_db()
    if meta_a.status != Meta.Status.PENDENTE:
        raise ScenarioError(f'reopen → pendente esperado, got {meta_a.status}')
    _ok('reopen → pendente')

    with audit_actor(lider):
        approve_meta(meta_a, lider)
    meta_a.refresh_from_db()
    if meta_a.status != Meta.Status.APROVADA:
        raise ScenarioError('reaprovação falhou')
    ok, motivo = can_advance(avaliacao)
    if not ok:
        raise ScenarioError(f'can_advance deveria permitir avanço: {motivo}')
    _ok('reaprovação permite avanço')


def scenario_c2(lider, colab, cargo_colab):
    print('C2 — Pós-reprovação de resultado')
    _ensure_no_open_cycle()
    today = timezone.localdate()
    ciclo = Ciclo.objects.create(
        nome=_unique('Ciclo C2'),
        data_inicio=today - timedelta(days=10),
        data_fim=today + timedelta(days=20),
        status=Ciclo.Status.ENCERRADO,
    )
    open_cycle(ciclo)
    avaliacao = Avaliacao.objects.get(ciclo=ciclo, usuario=colab)
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_RESULTADOS
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    objetivo = ObjetivoEstrategico.objects.create(descricao='Obj C2', ciclo=ciclo)
    meta = Meta.objects.create(
        usuario=colab,
        objetivo_estrategico=objetivo,
        descricao='Meta resultado',
        status=Meta.Status.APROVADA,
        status_resultado=Meta.StatusResultado.PENDENTE,
        progresso=50,
    )
    meta_ok = Meta.objects.create(
        usuario=colab,
        objetivo_estrategico=objetivo,
        descricao='Meta ok',
        status=Meta.Status.APROVADA,
        status_resultado=Meta.StatusResultado.APROVADO,
        progresso=100,
    )
    with audit_actor(lider):
        reject_resultado(meta, lider)
    meta.refresh_from_db()
    if meta.status_resultado != Meta.StatusResultado.REPROVADO:
        raise ScenarioError('resultado não ficou reprovado')
    _ok('reject_resultado')

    meta.progresso = 80
    meta.reopen_resultado()
    meta.save()
    meta.refresh_from_db()
    if meta.status_resultado != Meta.StatusResultado.PENDENTE:
        raise ScenarioError('reopen_resultado não → pendente')
    _ok('correção → pendente')

    with audit_actor(lider):
        approve_resultado(meta, lider)
    meta.refresh_from_db()
    meta_ok.refresh_from_db()
    if meta.status_resultado != Meta.StatusResultado.APROVADO:
        raise ScenarioError('reaprovação de resultado falhou')
    if meta_ok.status_resultado != Meta.StatusResultado.APROVADO:
        raise ScenarioError('irmão de resultado alterado')

    escala = Escala.objects.create(
        nome=_unique('Escala C2'),
        valor_minimo=1,
        valor_maximo=5,
    )
    competencia = Competencia.objects.create(
        nome=_unique('Comp C2'),
        tipo=Competencia.Tipo.TECNICA,
        escala=escala,
    )
    CargoCompetencia.objects.create(
        cargo=cargo_colab,
        competencia=competencia,
        nivel_esperado=Decimal('3.00'),
        peso=Decimal('1.00'),
    )

    ok, motivo = can_advance(avaliacao)
    if not ok:
        raise ScenarioError(f'can_advance deveria permitir avanço: {motivo}')
    _ok('reaprovação e irmãos intactos')


def scenario_c3(colab, cargo_colab, area, lider):
    print('C3 — Avaliação mid-cycle')
    _ensure_no_open_cycle()
    today = timezone.localdate()
    ciclo = Ciclo.objects.create(
        nome=_unique('Ciclo C3'),
        data_inicio=today - timedelta(days=5),
        data_fim=today + timedelta(days=25),
        status=Ciclo.Status.ENCERRADO,
    )
    open_cycle(ciclo)

    novo = CustomUser.objects.create_user(
        email=f'{_unique("mid")}@test.local',
        password=PASSWORD,
        nome='Mid Cycle',
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )
    created = ensure_avaliacao_for_user(novo)
    if created is None:
        raise ScenarioError('deveria criar Avaliação com ciclo aberto')
    if created.etapa != Avaliacao.Etapa.INPUT_METAS:
        raise ScenarioError('etapa inicial deveria ser input_metas')
    _ok('cria 1 Avaliação')

    again = ensure_avaliacao_for_user(novo)
    if again is None or again.pk != created.pk:
        raise ScenarioError('duplicata ou retorno inesperado')
    if Avaliacao.objects.filter(ciclo=ciclo, usuario=novo).count() != 1:
        raise ScenarioError('duplicata criada')
    _ok('idempotente')

    close_cycle(ciclo)
    outro = CustomUser.objects.create_user(
        email=f'{_unique("nocycle")}@test.local',
        password=PASSWORD,
        nome='Sem Ciclo',
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )
    noop = ensure_avaliacao_for_user(outro)
    if noop is not None:
        raise ScenarioError('sem ciclo aberto deveria ser no-op')
    _ok('no-op sem ciclo aberto')


def scenario_c4(admin, lider, colab, area, cargo_lider, cargo_colab):
    print('C4 — Catálogos + offboarding')
    escala_nome = _unique('Escala')
    escala = Escala.objects.create(
        nome=escala_nome,
        valor_minimo=1,
        valor_maximo=5,
    )
    competencia = Competencia.objects.create(
        nome=_unique('Comp'),
        tipo=Competencia.Tipo.TECNICA,
        escala=escala,
    )
    escala.is_active = False
    escala.save(update_fields=['is_active', 'updated_at'])
    competencia.is_active = False
    competencia.save(update_fields=['is_active', 'updated_at'])
    if Escala.objects.filter(pk=escala.pk, is_active=True).exists():
        raise ScenarioError('soft-delete de Escala falhou')
    _ok('soft-delete')

    Escala.objects.create(
        nome=escala_nome,
        valor_minimo=1,
        valor_maximo=5,
        is_active=True,
    )
    try:
        with transaction.atomic():
            Escala.objects.create(
                nome=escala_nome,
                valor_minimo=1,
                valor_maximo=5,
                is_active=True,
            )
        raise ScenarioError('unicidade de ativos não rejeitou duplicata')
    except (IntegrityError, ValidationError):
        _ok('unicidade ativos')

    lider_alvo = CustomUser.objects.create_user(
        email=f'{_unique("mgr")}@test.local',
        password=PASSWORD,
        nome='Gestor Offboard',
        cargo=cargo_lider,
        area=Area.objects.create(nome=_unique('Área2')),
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    report = CustomUser.objects.create_user(
        email=f'{_unique("rep")}@test.local',
        password=PASSWORD,
        nome='Liderado',
        cargo=cargo_colab,
        area=lider_alvo.area,
        line_manager=lider_alvo,
        email_confirmado_em=timezone.now(),
    )
    lider_alvo.is_active = False
    try:
        lider_alvo.save()
        raise ScenarioError('desativação com liderados deveria bloquear')
    except ValidationError:
        _ok('bloqueio com liderados')

    novo_gestor = CustomUser.objects.create_user(
        email=f'{_unique("newmgr")}@test.local',
        password=PASSWORD,
        nome='Novo Gestor',
        cargo=cargo_lider,
        area=lider_alvo.area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    with audit_actor(admin):
        count = reassign_direct_reports(
            from_manager=lider_alvo,
            to_manager=novo_gestor,
            actor=admin,
        )
    if count < 1:
        raise ScenarioError('reatribuição não moveu liderados')
    report.refresh_from_db()
    if report.line_manager_id != novo_gestor.pk:
        raise ScenarioError('liderado não reatribuído')
    lider_alvo.is_active = False
    lider_alvo.save()
    lider_alvo.refresh_from_db()
    if lider_alvo.is_active:
        raise ScenarioError('desativação após reassign falhou')
    _ok('reatribuição + desativação')


def scenario_c5(admin, lider, colab):
    print('C5 — Aprovação por admin')
    _ensure_no_open_cycle()
    today = timezone.localdate()
    ciclo = Ciclo.objects.create(
        nome=_unique('Ciclo C5'),
        data_inicio=today - timedelta(days=5),
        data_fim=today + timedelta(days=25),
        status=Ciclo.Status.ENCERRADO,
    )
    open_cycle(ciclo)
    avaliacao = Avaliacao.objects.get(ciclo=ciclo, usuario=colab)
    avaliacao.etapa = Avaliacao.Etapa.APROVACAO_METAS
    avaliacao.save(update_fields=['etapa', 'updated_at'])
    objetivo = ObjetivoEstrategico.objects.create(descricao='Obj C5', ciclo=ciclo)
    meta = Meta.objects.create(
        usuario=colab,
        objetivo_estrategico=objetivo,
        descricao='Meta admin',
        status=Meta.Status.PENDENTE,
    )
    with audit_actor(admin):
        approve_meta(meta, admin)
    meta.refresh_from_db()
    if meta.status != Meta.Status.APROVADA:
        raise ScenarioError('admin não aprovou')
    log = (
        AuditLog.objects.filter(
            entity_type='goals.Meta',
            entity_id=meta.pk,
            campo='status',
            valor_novo=Meta.Status.APROVADA,
        )
        .order_by('-created_at')
        .first()
    )
    if log is None or log.usuario_id != admin.pk:
        raise ScenarioError('AuditLog.actor não é o admin')
    _ok('admin approve + actor')

    lider_outro = CustomUser.objects.create_user(
        email=f'{_unique("out")}@test.local',
        password=PASSWORD,
        nome='Fora Escopo',
        cargo=lider.cargo,
        area=lider.area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    meta2 = Meta.objects.create(
        usuario=colab,
        objetivo_estrategico=objetivo,
        descricao='Meta negar',
        status=Meta.Status.PENDENTE,
    )
    try:
        with audit_actor(lider_outro):
            approve_meta(meta2, lider_outro)
        raise ScenarioError('líder fora do escopo deveria ser negado')
    except PermissionDenied:
        _ok('líder fora do escopo negado')


def scenario_c6(colab, ciclo_for_reminder=None):
    print('C6 — Lembretes e PDI')
    _ensure_no_open_cycle()
    today = timezone.localdate()
    reminder_days = int(getattr(settings, 'NOTIFICATION_REMINDER_DAYS', 3))
    target = today + timedelta(days=reminder_days)
    ciclo = Ciclo.objects.create(
        nome=_unique('Ciclo C6'),
        data_inicio=today - timedelta(days=5),
        data_fim=target,
        status=Ciclo.Status.ENCERRADO,
    )
    open_cycle(ciclo)
    with patch(
        'apps.notifications.tasks.send_lembrete_etapa_email',
    ) as send_mock:
        first = enviar_lembrete_prazo_etapa()
        second = enviar_lembrete_prazo_etapa()
    if first['enviados'] < 1:
        raise ScenarioError('primeiro job deveria enviar')
    if second['enviados'] != 0:
        raise ScenarioError('segundo job na mesma janela não deveria reenviar')
    if send_mock.call_count != first['enviados']:
        raise ScenarioError('contagem de envios incoerente com dedupe')
    _ok('dedupe lembrete (2× → 1)')

    pdi = PDI.objects.create(usuario=colab, titulo='PDI C6')
    past = today - timedelta(days=3)
    future = today + timedelta(days=7)
    acao = AcaoPDI.objects.create(
        pdi=pdi,
        descricao='Ação atrasada',
        responsavel=colab,
        prazo=past,
        status=AcaoPDI.Status.ATRASADA,
    )
    acao.prazo = future
    acao.save(update_fields=['prazo', 'updated_at'])
    acao.refresh_from_db()
    if acao.status != AcaoPDI.Status.PENDENTE:
        raise ScenarioError(
            f'extensão de prazo deveria limpar atraso, got {acao.status}',
        )
    if not AuditLog.objects.filter(
        entity_type='pdi.AcaoPDI',
        entity_id=acao.pk,
        campo='prazo',
    ).exists():
        raise ScenarioError('auditoria de prazo ausente')
    _ok('prazo futuro limpa atraso + audit')


def scenario_c7():
    print('C7 — Produção, testes e UX')
    client = Client()
    response = client.get(reverse('health'))
    if response.status_code != 200:
        raise ScenarioError(f'/health/ status {response.status_code}')
    payload = response.json()
    if payload.get('status') != 'ok' or payload.get('database') != 'ok':
        raise ScenarioError(f'/health/ payload inesperado: {payload}')
    _ok('GET /health/ 200')

    backup = REPO_ROOT / 'docs' / 'ops' / 'backup.md'
    if not backup.is_file():
        raise ScenarioError('docs/ops/backup.md ausente')
    text = backup.read_text(encoding='utf-8')
    if 'pg_dump' not in text:
        raise ScenarioError('backup.md sem procedimento pg_dump')
    _ok('backup.md aplicável')

    modal = (REPO_ROOT / 'templates' / 'components' / 'modal.html').read_text(
        encoding='utf-8',
    )
    js = (REPO_ROOT / 'static' / 'js' / 'modal.js').read_text(encoding='utf-8')
    empty = (
        REPO_ROOT / 'templates' / 'components' / 'empty_state.html'
    ).read_text(encoding='utf-8')
    indicator = (
        REPO_ROOT / 'templates' / 'components' / 'htmx_indicator.html'
    ).read_text(encoding='utf-8')
    if 'role="dialog"' not in modal or 'aria-modal="true"' not in modal:
        raise ScenarioError('modal sem a11y mínima')
    if 'Escape' not in js or 'lastTrigger' not in js:
        raise ScenarioError('modal.js sem Escape/restore')
    if 'cta_label' not in empty:
        raise ScenarioError('empty_state sem CTA condicional')
    if 'htmx-indicator' not in indicator:
        raise ScenarioError('htmx_indicator ausente')
    _ok('loading / empty / modal a11y')


def main() -> int:
    print('=== Quickstart C1–C7 (T042) ===')
    results: list[tuple[str, bool, str]] = []

    with transaction.atomic():
        sid = transaction.savepoint()
        try:
            area, cargo_lider, cargo_colab, admin, lider, colab = _make_users()

            for name, fn in [
                ('C1', lambda: scenario_c1(admin, lider, colab)),
                ('C2', lambda: scenario_c2(lider, colab, cargo_colab)),
                ('C3', lambda: scenario_c3(colab, cargo_colab, area, lider)),
                (
                    'C4',
                    lambda: scenario_c4(
                        admin,
                        lider,
                        colab,
                        area,
                        cargo_lider,
                        cargo_colab,
                    ),
                ),
                ('C5', lambda: scenario_c5(admin, lider, colab)),
                ('C6', lambda: scenario_c6(colab)),
                ('C7', scenario_c7),
            ]:
                try:
                    fn()
                    results.append((name, True, ''))
                except Exception as exc:  # noqa: BLE001
                    results.append((name, False, str(exc)))
                    _fail(name, exc)
                    traceback.print_exc()
        finally:
            transaction.savepoint_rollback(sid)
            # Garante que nada escape do rollback desta validação.
            transaction.set_rollback(True)

    print('\n=== Resumo ===')
    failed = 0
    for name, ok, err in results:
        status = 'PASS' if ok else 'FAIL'
        print(f'  {name}: {status}' + (f' — {err}' if err else ''))
        if not ok:
            failed += 1
    if failed:
        print(f'\n{failed} cenário(s) falharam.')
        return 1
    print('\nTodos os cenários C1–C7 passaram.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
