"""Seed mínimo para captura before do Design System v2 (T002).

Cria admin/líder/colab, ciclo aberto, PDI e classificação 9-box.
Idempotente: reutiliza e-mails de evidência se já existirem.

Uso (Docker):
  docker compose exec -T web python scripts/seed_evidence_007.py
"""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

import django

django.setup()

from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.cycles.models import Ciclo
from apps.cycles.services.cycle import close_cycle, open_cycle
from apps.organization.models import Area, Cargo
from apps.pdi.models import AcaoPDI, PDI
from apps.reviews.models import Avaliacao
from apps.talent.models import ClassificacaoTalento

PASSWORD = 'TestPass123!'


def upsert_user(*, email: str, **kwargs) -> CustomUser:
    user = CustomUser.objects.filter(email=email).first()
    if user is None:
        user = CustomUser.objects.create_user(email=email, password=PASSWORD, **kwargs)
        return user
    for key, value in kwargs.items():
        setattr(user, key, value)
    user.set_password(PASSWORD)
    user.save()
    return user


def main() -> None:
    area, _ = Area.objects.get_or_create(nome='Área Evidência DS v2')
    cargo_lider, _ = Cargo.objects.get_or_create(nome='Líder Evidência', defaults={'nivel': 2})
    cargo_colab, _ = Cargo.objects.get_or_create(nome='Analista Evidência', defaults={'nivel': 1})

    admin = upsert_user(
        email='admin@test.greenn.com.br',
        nome='Admin Teste',
        is_admin=True,
        is_staff=True,
        email_confirmado_em=timezone.now(),
    )
    lider = upsert_user(
        email='lider@test.greenn.com.br',
        nome='Líder Teste',
        cargo=cargo_lider,
        area=area,
        line_manager=admin,
        email_confirmado_em=timezone.now(),
    )
    colab = upsert_user(
        email='colab@test.greenn.com.br',
        nome='Colaborador Teste',
        cargo=cargo_colab,
        area=area,
        line_manager=lider,
        email_confirmado_em=timezone.now(),
    )

    for aberto in Ciclo.objects.filter(status=Ciclo.Status.ABERTO):
        close_cycle(aberto)

    today = date.today()
    ciclo = Ciclo.objects.filter(nome='Ciclo Evidência DS v2').first()
    if ciclo is None:
        ciclo = Ciclo.objects.create(
            nome='Ciclo Evidência DS v2',
            data_inicio=today - timedelta(days=30),
            data_fim=today + timedelta(days=60),
            status=Ciclo.Status.ENCERRADO,
        )
    if ciclo.status != Ciclo.Status.ABERTO:
        open_cycle(ciclo)
    ciclo.refresh_from_db()

    avaliacao = Avaliacao.objects.filter(ciclo=ciclo, usuario=colab).first()
    if avaliacao is None:
        avaliacao = Avaliacao.objects.create(ciclo=ciclo, usuario=colab)
    avaliacao.nota_final_lider = Decimal('0.50')
    avaliacao.save(update_fields=['nota_final_lider', 'updated_at'])

    ClassificacaoTalento.objects.update_or_create(
        usuario=colab,
        ciclo=ciclo,
        defaults={
            'desempenho': 2,
            'potencial': 2,
            'quadrante': ClassificacaoTalento.Quadrante.MEDIO_MEDIO,
            'visivel_ao_colaborador': False,
        },
    )

    pdi, _ = PDI.objects.get_or_create(
        usuario=colab,
        titulo='PDI Evidência DS v2',
        defaults={'status': PDI.Status.ATIVO},
    )
    if not pdi.acoes.exists():
        AcaoPDI.objects.create(
            pdi=pdi,
            descricao='Ação de desenvolvimento para evidência before',
            responsavel=lider,
            prazo=today + timedelta(days=30),
            status=AcaoPDI.Status.EM_ANDAMENTO,
        )

    print('SEED_OK')
    print(f'admin={admin.email}')
    print(f'lider={lider.email}')
    print(f'colab={colab.email}')
    print(f'ciclo_id={ciclo.pk} status={ciclo.status}')
    print(f'pdi_id={pdi.pk}')
    print(f'password={PASSWORD}')


if __name__ == '__main__':
    main()
