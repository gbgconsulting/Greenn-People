"""Validação T070 — 5 cenários quickstart + checks constitucionais.

Executa em transação com rollback (não persiste dados de teste).
Uso: python manage.py shell < scripts/_validate_t070.py
  ou: python scripts/_validate_t070.py (com DJANGO_SETTINGS_MODULE)
"""

from __future__ import annotations

import os
import sys
import time
import traceback
import uuid
from datetime import date, timedelta
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

import django

django.setup()

from django.conf import settings

# Django test Client usa Host: testserver
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver', 'localhost']

from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.accounts.services.scope import get_visible_users, user_in_scope
from apps.audit.models import AuditLog
from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.cycles.exceptions import CycleClosedError
from apps.cycles.models import Ciclo
from apps.cycles.services.cycle import close_cycle, open_cycle
from apps.cycles.services.stage import advance_stage
from apps.dashboard.models import AderenciaSnapshot
from apps.dashboard.services.adherence import compute_adherence
from apps.goals.models import Meta, ObjetivoEstrategico
from apps.goals.services.approval import approve_meta, approve_resultado
from apps.organization.models import Area, Cargo
from apps.pdi.models import AcaoPDI, PDI
from apps.pdi.services.progress import calculate_pdi_progress
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia
from apps.reviews.services.evaluation import (
    build_fr005_context,
    calcular_nota_final_autoavaliacao,
    calcular_nota_final_lider,
    create_competency_lines,
)
from apps.talent.models import ClassificacaoTalento
from apps.talent.services.classification import (
    derive_desempenho,
    upsert_classification,
)

results: list[tuple[str, bool, str]] = []
TAG = f't070-{uuid.uuid4().hex[:8]}'


def ok(name: str, detail: str = '') -> None:
    results.append((name, True, detail))
    print(f'  PASS  {name}' + (f' — {detail}' if detail else ''))


def fail(name: str, detail: str) -> None:
    results.append((name, False, detail))
    print(f'  FAIL  {name} — {detail}')


def check(name: str, condition: bool, detail: str = '') -> None:
    if condition:
        ok(name, detail)
    else:
        fail(name, detail or 'condição falsa')


def seed():
    """Cria hierarquia mínima admin -> líder -> colaborador + ciclo aberto."""
    # Fecha ciclos abertos existentes (rollback restaura).
    for c in Ciclo.objects.filter(status=Ciclo.Status.ABERTO):
        close_cycle(c)

    area = Area.objects.create(nome=f'Área {TAG}')
    cargo_lider = Cargo.objects.create(nome=f'Líder {TAG}', nivel=2)
    cargo_colab = Cargo.objects.create(nome=f'Analista {TAG}', nivel=1)

    escala = Escala.objects.create(
        nome=f'Escala {TAG}',
        valor_minimo=1,
        valor_maximo=5,
    )
    comp = Competencia.objects.create(
        nome=f'Comp {TAG}',
        tipo=Competencia.Tipo.TECNICA,
        escala=escala,
    )
    cc = CargoCompetencia.objects.create(
        cargo=cargo_colab,
        competencia=comp,
        nivel_esperado=Decimal('3.00'),
        peso=Decimal('1.00'),
    )

    admin = CustomUser.objects.create_user(
        email=f'admin-{TAG}@greenn.com.br',
        password='TestPass123!',
        nome=f'Admin {TAG}',
        is_admin=True,
        is_staff=True,
        email_confirmado_em=timezone.now(),
    )
    lider = CustomUser.objects.create_user(
        email=f'lider-{TAG}@greenn.com.br',
        password='TestPass123!',
        nome=f'Líder {TAG}',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    colaborador = CustomUser.objects.create_user(
        email=f'colab-{TAG}@greenn.com.br',
        password='TestPass123!',
        nome=f'Colab {TAG}',
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )
    outsider = CustomUser.objects.create_user(
        email=f'out-{TAG}@greenn.com.br',
        password='TestPass123!',
        nome=f'Outsider {TAG}',
        cargo=cargo_colab,
        area=area,
        email_confirmado_em=timezone.now(),
    )
    sem_cargo = CustomUser.objects.create_user(
        email=f'semcargo-{TAG}@greenn.com.br',
        password='TestPass123!',
        nome=f'Sem Cargo {TAG}',
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )

    today = date.today()
    ciclo = Ciclo.objects.create(
        nome=f'Ciclo {TAG}',
        data_inicio=today - timedelta(days=30),
        data_fim=today + timedelta(days=30),
        status=Ciclo.Status.ENCERRADO,
    )
    open_cycle(ciclo)
    ciclo.refresh_from_db()

    objetivo = ObjetivoEstrategico.objects.create(
        descricao=f'Objetivo {TAG}',
        ciclo=ciclo,
    )

    return {
        'area': area,
        'cargo_colab': cargo_colab,
        'cc': cc,
        'comp': comp,
        'escala': escala,
        'admin': admin,
        'lider': lider,
        'colaborador': colaborador,
        'outsider': outsider,
        'sem_cargo': sem_cargo,
        'ciclo': ciclo,
        'objetivo': objetivo,
    }


def cenario_1(ctx):
    print('\n=== Cenário 1 — Expectativas e desempenho (US1) ===')
    colab = ctx['colaborador']
    ciclo = ctx['ciclo']
    objetivo = ctx['objetivo']

    av = Avaliacao.objects.get(ciclo=ciclo, usuario=colab)
    check(
        'C1.1 Avaliacao criada no open_cycle',
        av.etapa == Avaliacao.Etapa.INPUT_METAS,
        f'etapa={av.etapa}',
    )

    fr005 = build_fr005_context(colab)
    check(
        'C1.2 Expectativas: competências + nível esperado',
        not fr005['vinculo_pendente'] and len(fr005.get('competencias_cargo', [])) >= 1,
        f'vinculo_pendente={fr005["vinculo_pendente"]}',
    )

    fr005_sem = build_fr005_context(ctx['sem_cargo'])
    check(
        'C1.2b Sem cargo -> vinculo_pendente',
        fr005_sem['vinculo_pendente'] is True,
    )

    meta = Meta.objects.create(
        usuario=colab,
        objetivo_estrategico=objetivo,
        descricao=f'Meta {TAG}',
    )
    check('C1.3 Meta status=pendente', meta.status == Meta.Status.PENDENTE)

    # Avança até resultados via líder
    advance_stage(av, colab)
    av.refresh_from_db()
    approve_meta(meta, ctx['lider'])
    advance_stage(av, ctx['lider'])
    av.refresh_from_db()
    check('C1.4 Etapa resultados após aprovação', av.etapa == Avaliacao.Etapa.RESULTADOS)

    meta.progresso = Decimal('80.00')
    meta.save(update_fields=['progresso', 'updated_at'])
    meta.refresh_from_db()
    check('C1.5 Progresso salvo', meta.progresso == Decimal('80.00'))

    advance_stage(av, colab)
    av.refresh_from_db()
    approve_resultado(meta, ctx['lider'])
    advance_stage(av, ctx['lider'])
    av.refresh_from_db()
    check('C1.6 Entrou em avaliacao (snapshots)', av.etapa == Avaliacao.Etapa.AVALIACAO)

    linhas = list(AvaliacaoCompetencia.objects.filter(avaliacao=av))
    check('C1.7 Linhas de competência criadas', len(linhas) >= 1)

    for linha in linhas:
        linha.nota_autoavaliacao = Decimal('4.00')
        linha.save(update_fields=['nota_autoavaliacao', 'updated_at'])

    calcular_nota_final_autoavaliacao(av)
    av.refresh_from_db()
    check(
        'C1.8 nota_autoavaliacao registrada',
        av.nota_final_autoavaliacao is not None,
        f'nota={av.nota_final_autoavaliacao}',
    )

    ctx['avaliacao'] = av
    ctx['meta'] = meta
    ctx['linhas'] = linhas


def cenario_2(ctx):
    print('\n=== Cenário 2 — Líder avalia equipe (US2) ===')
    lider = ctx['lider']
    colab = ctx['colaborador']
    outsider = ctx['outsider']
    av = ctx['avaliacao']

    check('C2.1 Líder is_leader', lider.is_leader is True)

    visible = set(get_visible_users(lider).values_list('pk', flat=True))
    check('C2.2 Colaborador no escopo do líder', colab.pk in visible)
    check(
        'C2.2b Outsider fora do escopo',
        not user_in_scope(lider, outsider.pk),
    )

    # Nota líder + consolidada
    for linha in ctx['linhas']:
        linha.nota_lider = Decimal('5.00')
        linha.save(update_fields=['nota_lider', 'updated_at'])

    nota = calcular_nota_final_lider(av)
    av.refresh_from_db()
    check(
        'C2.3 nota_final_lider calculada',
        av.nota_final_lider is not None and nota == av.nota_final_lider,
        f'nota={av.nota_final_lider}',
    )

    # IDOR via client
    client = Client()
    client.force_login(lider)
    # Avaliação do outsider (fora do escopo)
    av_out = Avaliacao.objects.get(ciclo=ctx['ciclo'], usuario=outsider)
    url = reverse('reviews:detail', kwargs={'pk': av_out.pk})
    before_audit = AuditLog.objects.filter(acao=AuditLog.Acao.ACCESS_DENIED).count()
    resp = client.get(url)
    after_audit = AuditLog.objects.filter(acao=AuditLog.Acao.ACCESS_DENIED).count()
    check('C2.4 IDOR -> 404', resp.status_code == 404, f'status={resp.status_code}')
    check(
        'C2.5 IDOR gera AuditLog access_denied',
        after_audit > before_audit,
        f'before={before_audit} after={after_audit}',
    )

    # Team dashboard
    resp_team = client.get(reverse('dashboard:team'))
    check(
        'C2.6 Dashboard time acessível ao líder',
        resp_team.status_code == 200,
        f'status={resp_team.status_code}',
    )


def cenario_3(ctx):
    print('\n=== Cenário 3 — PDI (US3) ===')
    colab = ctx['colaborador']
    lider = ctx['lider']

    pdi = PDI.objects.create(usuario=colab, titulo=f'PDI {TAG}')
    acao_colab = AcaoPDI.objects.create(
        pdi=pdi,
        descricao=f'Ação colaborador {TAG}',
        responsavel=colab,
        prazo=date.today() + timedelta(days=14),
    )
    check('C3.1 PDI criado', PDI.objects.filter(pk=pdi.pk).exists())

    acao_lider = AcaoPDI.objects.create(
        pdi=pdi,
        descricao=f'Ação líder {TAG}',
        responsavel=lider,
        prazo=date.today() + timedelta(days=21),
    )
    check(
        'C3.2 Líder cria ação no PDI do liderado',
        AcaoPDI.objects.filter(pk=acao_lider.pk, pdi=pdi).exists(),
    )

    before = acao_colab.updated_at
    time.sleep(0.05)
    before_audit = AuditLog.objects.filter(
        entity_type='pdi.AcaoPDI',
        entity_id=acao_colab.pk,
        acao=AuditLog.Acao.UPDATE,
    ).count()
    acao_colab.status = AcaoPDI.Status.EM_ANDAMENTO
    acao_colab.save(update_fields=['status', 'updated_at'])
    acao_colab.refresh_from_db()
    after_audit = AuditLog.objects.filter(
        entity_type='pdi.AcaoPDI',
        entity_id=acao_colab.pk,
        acao=AuditLog.Acao.UPDATE,
    ).count()
    check('C3.3 updated_at alterado', acao_colab.updated_at > before)
    check(
        'C3.4 Auditoria de status AcaoPDI',
        after_audit > before_audit,
        f'before={before_audit} after={after_audit}',
    )

    progress = calculate_pdi_progress(pdi)
    check('C3.5 calculate_pdi_progress retorna Decimal', isinstance(progress, Decimal))

    # Independente do ciclo: cria PDI com ciclo encerrado depois (validado no C4)
    ctx['pdi'] = pdi


def cenario_4(ctx):
    print('\n=== Cenário 4 — Ciclos e aderência (US4) ===')
    ciclo = ctx['ciclo']
    admin = ctx['admin']
    lider = ctx['lider']

    active_count = CustomUser.objects.filter(is_active=True).count()
    av_count = Avaliacao.objects.filter(ciclo=ciclo).count()
    check(
        'C4.1 Avaliacoes para todos is_active',
        av_count >= active_count,
        f'avaliacoes={av_count} ativos={active_count}',
    )

    # Snapshot via serviço (task Celery pode falhar sem Redis — chama sync)
    percentual, componentes = compute_adherence(lider.pk, ciclo.pk)
    snap, _ = AderenciaSnapshot.objects.update_or_create(
        lider=lider,
        ciclo=ciclo,
        defaults={
            'percentual': percentual,
            'componentes': componentes,
            'calculado_em': timezone.now(),
        },
    )
    check(
        'C4.2 AderenciaSnapshot persistido',
        AderenciaSnapshot.objects.filter(pk=snap.pk).exists(),
        f'percentual={snap.percentual}',
    )

    client = Client()
    client.force_login(admin)
    t0 = time.perf_counter()
    resp = client.get(reverse('dashboard:adherence'))
    elapsed = time.perf_counter() - t0
    check('C4.3 Painel aderência 200', resp.status_code == 200)
    check(
        'C4.3b Dashboard aderência < 2s',
        elapsed < 2.0,
        f'{elapsed:.3f}s',
    )
    # Confirma que a view lê snapshot (conteúdo presente)
    check(
        'C4.3c Resposta contém percentual do snapshot',
        str(int(snap.percentual)) in resp.content.decode('utf-8')
        or f'{snap.percentual}' in resp.content.decode('utf-8'),
    )

    resp_struct = client.get(reverse('dashboard:structure'))
    check(
        'C4.4 Lacunas estrutura 200',
        resp_struct.status_code == 200,
        f'status={resp_struct.status_code}',
    )

    close_cycle(ciclo)
    ciclo.refresh_from_db()
    check('C4.5 Ciclo encerrado', ciclo.status == Ciclo.Status.ENCERRADO)

    av = ctx['avaliacao']
    av.refresh_from_db()
    raised = False
    try:
        advance_stage(av, ctx['lider'])
    except CycleClosedError:
        raised = True
    check('C4.6 advance_stage bloqueado (CycleClosedError)', raised)

    # PDI ainda funciona com ciclo encerrado
    pdi2 = PDI.objects.create(usuario=ctx['colaborador'], titulo=f'PDI pós-ciclo {TAG}')
    check('C4.7 PDI independente do ciclo aberto', pdi2.pk is not None)


def cenario_5(ctx):
    print('\n=== Cenário 5 — Matriz 9-box (US5) ===')
    # Reabre ciclo para classificação (upsert precisa de Avaliacao com nota)
    # close_cycle já rodou; reopen
    open_cycle(ctx['ciclo'])
    ctx['ciclo'].refresh_from_db()

    colab = ctx['colaborador']
    admin = ctx['admin']
    ciclo = ctx['ciclo']
    av = Avaliacao.objects.get(ciclo=ciclo, usuario=colab)
    # Garante nota_final_lider
    if av.nota_final_lider is None:
        linhas = list(AvaliacaoCompetencia.objects.filter(avaliacao=av))
        if not linhas:
            create_competency_lines(av)
            linhas = list(AvaliacaoCompetencia.objects.filter(avaliacao=av))
        for linha in linhas:
            linha.nota_lider = Decimal('5.00')
            linha.save(update_fields=['nota_lider', 'updated_at'])
        calcular_nota_final_lider(av)
        av.refresh_from_db()

    expected_desemp = derive_desempenho(av.nota_final_lider)
    classif = upsert_classification(colab, ciclo, potencial=3, admin=admin)
    check(
        'C5.1 potencial manual salvo',
        classif.potencial == 3,
    )
    check(
        'C5.2 desempenho derivado de nota_final_lider',
        classif.desempenho == expected_desemp,
        f'desempenho={classif.desempenho} expected={expected_desemp}',
    )
    check(
        'C5.2b visivel_ao_colaborador default False',
        classif.visivel_ao_colaborador is False,
    )

    client = Client()
    # Matriz exige is_manager (2+ níveis) ou is_admin — quickstart: gestor/RH.
    client.force_login(admin)
    resp = client.get(reverse('talent:matrix') + f'?area={ctx["area"].pk}')
    check(
        'C5.3 Matriz filtrável por área (admin/gestor)',
        resp.status_code == 200,
        f'status={resp.status_code}',
    )
    # Líder direto (só is_leader) não acessa a matriz — RequiresManagerOrAdminMixin
    client.force_login(ctx['lider'])
    resp_lider = client.get(reverse('talent:matrix'))
    check(
        'C5.3b Líder sem is_manager recebe 403 na matriz',
        resp_lider.status_code == 403,
        f'status={resp_lider.status_code}',
    )

    client.force_login(colab)
    resp_mine = client.get(reverse('talent:mine'))
    check('C5.4 Colaborador acessa /talent/mine/', resp_mine.status_code == 200)
    ctx_view = getattr(resp_mine, 'context', None)
    oculto_flag = False
    if ctx_view is not None:
        oculto_flag = bool(ctx_view.get('classificacao_oculta')) or (
            ctx_view.get('classificacao') is None
        )
    body = resp_mine.content.decode('utf-8').lower()
    check(
        'C5.4b Template indica classificação oculta',
        oculto_flag
        or 'oculta' in body
        or 'não disponível' in body
        or 'nao disponivel' in body
        or 'ainda não' in body
        or 'ainda nao' in body
        or 'liberad' in body,
        'contexto ou texto de ocultação',
    )

    visible_qs = ClassificacaoTalento.objects.filter(
        usuario=colab,
        ciclo=ciclo,
        visivel_ao_colaborador=True,
    )
    check(
        'C5.5 Sem visibilidade liberada -> não vê classificação',
        not visible_qs.exists(),
    )


def checks_constitucionais(ctx):
    print('\n=== Checks constitucionais ===')

    # Snapshots write-once
    linha = AvaliacaoCompetencia.objects.filter(
        avaliacao__usuario=ctx['colaborador'],
        avaliacao__ciclo=ctx['ciclo'],
    ).first()
    check('CONST.1 Linha de snapshot existe', linha is not None)
    if linha:
        original_peso = linha.peso_utilizado
        ctx['cc'].peso = Decimal('9.99')
        ctx['cc'].save(update_fields=['peso', 'updated_at'])
        # Recalcular nota não deve alterar snapshot
        try:
            linha.peso_utilizado = Decimal('9.99')
            linha.save()
            fail('CONST.2 Snapshot write-once', 'save() aceitou alteração de peso_utilizado')
        except ValidationError:
            ok('CONST.2 Snapshot write-once bloqueia alteração', f'peso={original_peso}')

        # Nota permanece baseada no snapshot (peso_utilizado original)
        linha.refresh_from_db()
        check(
            'CONST.2b peso_utilizado inalterado após mudança CargoCompetencia',
            linha.peso_utilizado == original_peso,
            f'snapshot={linha.peso_utilizado} cargo_atual={ctx["cc"].peso}',
        )

    # Audit append-only
    log = AuditLog.objects.order_by('-pk').first()
    check('CONST.3 AuditLog existe', log is not None)
    if log:
        try:
            log.campo = 'hacked'
            log.save()
            fail('CONST.4 Audit append-only (update)', 'save() permitiu alteração')
        except ValidationError:
            ok('CONST.4 Audit append-only (update) bloqueado')
        try:
            log.delete()
            fail('CONST.5 Audit append-only (delete)', 'delete() permitido')
        except ValidationError:
            ok('CONST.5 Audit append-only (delete) bloqueado')

    from apps.audit.admin import AuditLogAdmin
    from django.contrib.admin.sites import AdminSite

    admin_inst = AuditLogAdmin(AuditLog, AdminSite())
    check(
        'CONST.6 Admin sem change/delete/add',
        (
            not admin_inst.has_add_permission(None)
            and not admin_inst.has_change_permission(None)
            and not admin_inst.has_delete_permission(None)
        ),
    )

    # Paginação
    from apps.core.mixins import HtmxPaginatedListMixin

    check(
        'CONST.7 paginate_by=20 no mixin',
        HtmxPaginatedListMixin.paginate_by == 20,
    )

    # Escopo já validado em C2
    check(
        'CONST.8 Escopo backend (já C2.4/C2.5)',
        any(n.startswith('C2.4') and p for n, p, _ in results),
    )


def main():
    print(f'T070 validação — tag={TAG}')
    print('Ambiente: rollback ao final (dados de teste não persistem)\n')

    with transaction.atomic():
        sid = transaction.savepoint()
        try:
            ctx = seed()
            cenario_1(ctx)
            cenario_2(ctx)
            cenario_3(ctx)
            cenario_4(ctx)
            cenario_5(ctx)
            checks_constitucionais(ctx)
        except Exception as exc:
            fail('RUNTIME', f'{type(exc).__name__}: {exc}')
            traceback.print_exc()
        finally:
            transaction.savepoint_rollback(sid)

    passed = sum(1 for _, p, _ in results if p)
    failed = sum(1 for _, p, _ in results if not p)
    print('\n' + '=' * 60)
    print(f'Resultado: {passed} PASS / {failed} FAIL / {len(results)} total')
    if failed:
        print('\nFalhas:')
        for name, p, detail in results:
            if not p:
                print(f'  - {name}: {detail}')
        sys.exit(1)
    print('\nTodos os checks do T070 passaram.')
    sys.exit(0)


if __name__ == '__main__':
    main()
