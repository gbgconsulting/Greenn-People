"""Validação guiada quickstart 017 — cenários A–F + gate visual (T037).

Executa em transação com rollback (não persiste seed).

Uso:
  .venv/bin/python scripts/validate_quickstart_017_pdi.py
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
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

from django.db import transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.notifications.models import NotificacaoLog
from apps.notifications.tasks import (
    enviar_alerta_acao_pdi_atrasada,
    enviar_digest_pdi_atrasos,
)
from apps.organization.models import Area, Cargo
from apps.pdi.models import AcaoPDI, PDI
from apps.pdi.services.lifecycle import (
    PDINotCompletableError,
    complete_pdi,
    pdi_can_complete,
)

PASSWORD = 'Validate017!'
FIXTURE_DATA_ENTRADA = date(2020, 1, 15)
stamp = timezone.now().strftime('%Y%m%d%H%M%S%f')
results: list[tuple] = []


def _ok(name: str) -> None:
    results.append(('PASS', name))
    print(f'  ✓ {name}')


def _fail(name: str, exc: BaseException) -> None:
    results.append(('FAIL', name, str(exc)))
    print(f'  ✗ {name}: {exc}')


def _unique(prefix: str) -> str:
    return f'{prefix}-{stamp}'


def _criar_acao(pdi: PDI, *, responsavel: CustomUser, status: str, prazo, descricao: str):
    return AcaoPDI.objects.create(
        pdi=pdi,
        descricao=descricao,
        responsavel=responsavel,
        prazo=prazo,
        status=status,
    )


@transaction.atomic
def run() -> None:
    sid = transaction.savepoint()
    try:
        area = Area.objects.create(nome=_unique('Area017'))
        cargo_lider = Cargo.objects.create(nome=_unique('CargoLider017'), nivel=2)
        cargo_colab = Cargo.objects.create(nome=_unique('CargoColab017'), nivel=1)

        admin = CustomUser.objects.create_user(
            email=f'admin-{stamp}@test.greenn.com.br',
            password=PASSWORD,
            nome='Admin 017',
            is_admin=True,
            is_staff=True,
            data_entrada=FIXTURE_DATA_ENTRADA,
            email_confirmado_em=timezone.now(),
        )
        gestor = CustomUser.objects.create_user(
            email=f'gestor-{stamp}@test.greenn.com.br',
            password=PASSWORD,
            nome='Gestor 017',
            cargo=cargo_lider,
            area=area,
            line_manager=admin,
            data_entrada=FIXTURE_DATA_ENTRADA,
            email_confirmado_em=timezone.now(),
        )
        colab = CustomUser.objects.create_user(
            email=f'colab-{stamp}@test.greenn.com.br',
            password=PASSWORD,
            nome='Colab 017',
            cargo=cargo_colab,
            area=area,
            line_manager=gestor,
            data_entrada=FIXTURE_DATA_ENTRADA,
            email_confirmado_em=timezone.now(),
        )
        outsider = CustomUser.objects.create_user(
            email=f'outro-{stamp}@test.greenn.com.br',
            password=PASSWORD,
            nome='Outro 017',
            cargo=cargo_colab,
            area=area,
            data_entrada=FIXTURE_DATA_ENTRADA,
            email_confirmado_em=timezone.now(),
        )

        ontem = timezone.localdate() - timedelta(days=1)
        futuro = timezone.localdate() + timedelta(days=10)

        pdi_atrasado = PDI.objects.create(
            usuario=colab,
            titulo='PDI com atraso',
            status=PDI.Status.ATIVO,
        )
        pdi_ok = PDI.objects.create(
            usuario=colab,
            titulo='PDI sem atraso',
            status=PDI.Status.ATIVO,
        )
        pdi_outro = PDI.objects.create(
            usuario=outsider,
            titulo='PDI alheio',
            status=PDI.Status.ATIVO,
        )

        # Pendente com prazo ontem → mark_overdue marca atrasada (cenário B).
        # Isolada por descrição única; não rodar mark_overdue org-wide sem filtro.
        acao_a_marcar = _criar_acao(
            pdi_atrasado,
            responsavel=colab,
            status=AcaoPDI.Status.PENDENTE,
            prazo=ontem,
            descricao='Ação vencida T037',
        )
        _criar_acao(
            pdi_ok,
            responsavel=colab,
            status=AcaoPDI.Status.PENDENTE,
            prazo=futuro,
            descricao='Ação no prazo',
        )
        # Já atrasada no PDI alheio (controle de leak).
        _criar_acao(
            pdi_outro,
            responsavel=outsider,
            status=AcaoPDI.Status.ATRASADA,
            prazo=ontem,
            descricao='Ação outro',
        )
        # Badge no hub exige ação já atrasada no escopo do gestor.
        _criar_acao(
            pdi_atrasado,
            responsavel=colab,
            status=AcaoPDI.Status.ATRASADA,
            prazo=ontem - timedelta(days=2),
            descricao='Ação já atrasada',
        )

        c = Client()

        # --- A. Hub ---
        print('\n### A. Hub — filtro e badge')
        try:
            assert c.login(username=gestor.email, password=PASSWORD)
            r = c.get(reverse('pdi:list') + '?visao=equipe')
            assert r.status_code == 200
            body = r.content.decode()
            assert 'Com atrasadas' in body
            assert 'atrasada' in body.lower()
            _ok('A1 gestor vê chip Com atrasadas e badge no escopo')
        except Exception as e:
            _fail('A1 gestor hub', e)

        try:
            r = c.get(reverse('pdi:list') + '?visao=equipe&atrasadas=1')
            assert r.status_code == 200
            body = r.content.decode()
            assert 'PDI com atraso' in body
            assert 'PDI sem atraso' not in body
            _ok('A2 chip atrasadas=1 filtra só com atraso')
        except Exception as e:
            _fail('A2 filtro atrasadas', e)

        try:
            c.logout()
            assert c.login(username=colab.email, password=PASSWORD)
            r = c.get(reverse('pdi:list') + '?atrasadas=1')
            body = r.content.decode()
            assert 'PDI alheio' not in body
            assert 'PDI com atraso' in body
            _ok('A3 colaborador sem vazamento')
        except Exception as e:
            _fail('A3 colaborador escopo', e)

        try:
            c.logout()
            c.login(username=gestor.email, password=PASSWORD)
            r = c.get(reverse('pdi:list') + '?visao=equipe')
            body = r.content.decode()
            assert 'font-display' in body
            assert 'Novo plano' in body
            assert 'rounded-lg' in body
            _ok('A-visual Fraunces + CTA Novo plano + rounded-lg')
        except Exception as e:
            _fail('A-visual', e)

        # --- B. Alerta ---
        # Em DB compartilhado não rodamos mark_overdue org-wide (evita side-effects).
        # Cobertura de enqueue on_commit: pytest test_mark_overdue_enfileira_*.
        # Aqui validamos o contrato pontual dono+gestor + dedupe com send mockado.
        print('\n### B. Alerta de atraso')
        try:
            acao_a_marcar.status = AcaoPDI.Status.ATRASADA
            acao_a_marcar.save(update_fields=['status', 'updated_at'])
            with patch(
                'apps.notifications.tasks.send_atraso_pdi_email',
            ) as send_mock:
                out = enviar_alerta_acao_pdi_atrasada(acao_a_marcar.pk)
            assert out['enviados'] == 2
            assert send_mock.call_count == 2
            dest_ids = {call.args[1].pk for call in send_mock.call_args_list}
            assert dest_ids == {colab.pk, gestor.pk}
            logs = NotificacaoLog.objects.filter(
                tipo=NotificacaoLog.Tipo.ATRASO_PDI,
                referencia=f'acao_pdi:{acao_a_marcar.pk}',
                status=NotificacaoLog.Status.ENVIADO,
            )
            assert set(logs.values_list('destinatario_id', flat=True)) == {
                colab.pk,
                gestor.pk,
            }
            _ok('B1 atraso_pdi para dono e gestor (send mockado)')
        except Exception as e:
            _fail('B1 alerta dono+gestor', e)

        try:
            before = NotificacaoLog.objects.filter(
                tipo=NotificacaoLog.Tipo.ATRASO_PDI,
                referencia=f'acao_pdi:{acao_a_marcar.pk}',
            ).count()
            with patch('apps.notifications.tasks.send_atraso_pdi_email') as send_mock:
                enviar_alerta_acao_pdi_atrasada(acao_a_marcar.pk)
            after = NotificacaoLog.objects.filter(
                tipo=NotificacaoLog.Tipo.ATRASO_PDI,
                referencia=f'acao_pdi:{acao_a_marcar.pk}',
            ).count()
            assert after == before
            assert send_mock.call_count == 0
            _ok('B2 segunda run mesmo dia = dedupe')
        except Exception as e:
            _fail('B2 dedupe', e)

        # --- C. Tabela ---
        print('\n### C. Tabela operacional')
        try:
            c.logout()
            c.login(username=gestor.email, password=PASSWORD)
            r = c.get(reverse('pdi:list') + '?visao=equipe&modo=tabela')
            body = r.content.decode()
            assert r.status_code == 200
            assert 'leader-team-table' in body
            assert 'Atrasadas' in body
            assert 'Filtros' in body
            assert 'faixa_atraso' in body
            assert 'pdi-modo-toggle' in body
            _ok('C1 gestor vê tabela + filtros + toggle')
        except Exception as e:
            _fail('C1 tabela gestor', e)

        try:
            c.logout()
            c.login(username=colab.email, password=PASSWORD)
            r = c.get(reverse('pdi:list') + '?modo=tabela')
            body = r.content.decode()
            assert 'leader-team-table' not in body
            assert 'pdi-modo-toggle' not in body
            _ok('C2 colaborador sem toggle/tabela')
        except Exception as e:
            _fail('C2 colaborador sem tabela', e)

        # --- D. Digest ---
        # Destinatários restritos ao admin seed + send mock (sem e-mail org real).
        print('\n### D. Digest admin')
        try:
            admin_qs = CustomUser.objects.filter(pk=admin.pk)

            def _filter_admins(*args, **kwargs):
                if kwargs.get('is_admin') is True:
                    return admin_qs
                return CustomUser.objects.filter(*args, **kwargs)

            with (
                patch(
                    'apps.notifications.tasks.CustomUser.objects.filter',
                    side_effect=_filter_admins,
                ),
                patch(
                    'apps.notifications.tasks.send_digest_pdi_atrasos_email',
                ) as send_digest_mock,
            ):
                out = enviar_digest_pdi_atrasos()
            if out.get('resultado') == 'silencio':
                raise AssertionError('digest silencioso com ações atrasadas no seed')
            assert NotificacaoLog.objects.filter(
                tipo=NotificacaoLog.Tipo.DIGEST_PDI_ATRASOS,
                destinatario=admin,
            ).exists()
            assert not NotificacaoLog.objects.filter(
                tipo=NotificacaoLog.Tipo.DIGEST_PDI_ATRASOS,
                destinatario=gestor,
            ).exists()
            assert send_digest_mock.called
            _ok('D1 digest só admin seed; gestor não recebe')
        except Exception as e:
            _fail('D1 digest admin', e)

        # --- E. Widget ---
        print('\n### E. Widget dashboard')
        try:
            c.logout()
            c.login(username=gestor.email, password=PASSWORD)
            team_url = reverse('dashboard:team')
            r = c.get(team_url)
            assert r.status_code == 200
            body = r.content.decode()
            assert 'Ações atrasadas' in body
            assert 'Ver PDIs atrasados' in body
            assert 'atrasadas=1' in body
            _ok('E1 widget time com contagem e link atrasadas=1')
        except Exception as e:
            _fail('E1 widget time', e)

        try:
            c.logout()
            c.login(username=admin.email, password=PASSWORD)
            admin_url = reverse('dashboard:admin')
            r = c.get(admin_url)
            assert r.status_code == 200
            body = r.content.decode()
            assert 'Ações atrasadas' in body
            # Zero neutro: accent=neutral quando sem atraso no template;
            # aqui há atrasos → warning ok. Confirma card presente.
            assert 'Ver PDIs atrasados' in body
            _ok('E2 widget admin presente com CTA')
        except Exception as e:
            _fail('E2 widget admin', e)

        # --- F. Board + concluir ---
        print('\n### F. Board + concluir')
        try:
            c.logout()
            c.login(username=colab.email, password=PASSWORD)
            r = c.get(reverse('pdi:detail', kwargs={'pk': pdi_atrasado.pk}))
            body = r.content.decode()
            assert 'Atrasadas' in body
            assert 'acoes-atrasadas-heading' in body
            _ok('F1 coluna Atrasadas isolada no board')
        except Exception as e:
            _fail('F1 board coluna', e)

        try:
            assert not pdi_can_complete(pdi_atrasado)
            try:
                complete_pdi(pdi_atrasado)
                raise AssertionError('deveria rejeitar com ação aberta')
            except PDINotCompletableError:
                pass
            r = c.get(reverse('pdi:detail', kwargs={'pk': pdi_atrasado.pk}))
            assert 'Concluir plano' not in r.content.decode()
            _ok('F2 com ação aberta: complete rejeita e CTA ausente')
        except Exception as e:
            _fail('F2 complete rejeita', e)

        try:
            for a in pdi_atrasado.acoes.all():
                a.status = AcaoPDI.Status.CONCLUIDA
                a.save(update_fields=['status'])
            assert pdi_can_complete(pdi_atrasado)
            r = c.get(reverse('pdi:detail', kwargs={'pk': pdi_atrasado.pk}))
            assert 'Concluir plano' in r.content.decode()
            complete_pdi(pdi_atrasado)
            pdi_atrasado.refresh_from_db()
            assert pdi_atrasado.status == PDI.Status.CONCLUIDO
            _ok('F3 100% concluídas → CTA + status concluido')
        except Exception as e:
            _fail('F3 complete ok', e)

        # --- Gate visual ---
        print('\n### Gate visual (ui-visual-consistency)')
        try:
            c.logout()
            c.login(username=gestor.email, password=PASSWORD)
            r = c.get(reverse('pdi:list') + '?visao=equipe&modo=tabela')
            body = r.content.decode()
            checks = {
                'h1 Fraunces / font-display': 'font-display' in body,
                'chip Com atrasadas emerald': 'Com atrasadas' in body
                and 'bg-emerald-50' in body,
                'filtros em details': '<details' in body and 'Filtros' in body,
                'tabela leader-team-table': 'leader-team-table' in body,
                'CTA Novo plano soberano': 'Novo plano' in body,
                'rounded-lg controles': 'rounded-lg' in body,
                'toggle DNA ownership': 'pdi-modo-toggle' in body
                and 'bg-brand-gradient' in body,
            }
            missing = [k for k, v in checks.items() if not v]
            assert not missing, f'faltando: {missing}'
            _ok('Gate visual hub/tabela OK')
        except Exception as e:
            _fail('Gate visual', e)

        # Zero neutro no dashboard (widget E)
        try:
            # remove atrasos do escopo do gestor temporariamente via concluir/arquivar
            # — já concluímos pdi_atrasado; pdi_ok sem atraso.
            # Marca ação do outsider fora do escopo; widget do gestor deve zerar.
            c.logout()
            c.login(username=gestor.email, password=PASSWORD)
            r = c.get(reverse('dashboard:team'))
            body = r.content.decode()
            # Após concluir o único PDI com atraso no escopo, zero neutro.
            assert 'Ações atrasadas' in body
            assert 'Nenhuma ação atrasada no escopo' in body or 'value">0<' in body or '>0<' in body
            _ok('E-visual zero/estado widget após limpar atrasos do escopo')
        except Exception as e:
            _fail('E-visual zero', e)

    finally:
        transaction.savepoint_rollback(sid)
        print('\n(rollback — sem persistir seed)')


if __name__ == '__main__':
    run()
    fails = [r for r in results if r[0] == 'FAIL']
    print(f'\n=== RESUMO T037: {len(results) - len(fails)}/{len(results)} PASS ===')
    sys.exit(1 if fails else 0)
