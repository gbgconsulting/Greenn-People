"""T020 — prazo 20d corridos + atraso sinalizável (sem auto-close)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from apps.cycles.models import Ciclo
from apps.cycles.services.prazo import (
    PRAZO_DIAS_CORRIDOS,
    ciclos_automaticos_em_atraso,
    data_fim_from_inicio,
    is_prazo_estourado,
)


@pytest.mark.django_db
def test_data_fim_from_inicio_vinte_dias_corridos():
    assert PRAZO_DIAS_CORRIDOS == 20
    inicio = date(2026, 7, 1)
    assert data_fim_from_inicio(inicio) == inicio + timedelta(days=20)
    # Corridos: inclui fins de semana (não é +20 dias úteis).
    assert data_fim_from_inicio(inicio).weekday() == date(2026, 7, 21).weekday()


@pytest.mark.django_db
def test_prazo_estourado_somente_apos_data_fim_com_aberto():
    ciclo = Ciclo.objects.create(
        nome='Auto Jul',
        data_inicio=date(2026, 7, 1),
        data_fim=date(2026, 7, 21),
        status=Ciclo.Status.ABERTO,
        origem=Ciclo.Origem.AUTOMATICO,
        marco_competencia=date(2026, 7, 1),
    )
    assert is_prazo_estourado(ciclo, ref_date=date(2026, 7, 21)) is False
    assert is_prazo_estourado(ciclo, ref_date=date(2026, 7, 22)) is True

    ciclo.status = Ciclo.Status.ENCERRADO
    ciclo.save(update_fields=['status', 'updated_at'])
    assert is_prazo_estourado(ciclo, ref_date=date(2026, 8, 1)) is False
    assert ciclo.prazo_estourado is False


@pytest.mark.django_db
def test_ciclos_automaticos_em_atraso_query_para_governanca():
    auto_atrasado = Ciclo.objects.create(
        nome='Auto atrasado',
        data_inicio=date(2026, 6, 1),
        data_fim=date(2026, 6, 21),
        status=Ciclo.Status.ABERTO,
        origem=Ciclo.Origem.AUTOMATICO,
        marco_competencia=date(2026, 6, 1),
    )
    Ciclo.objects.create(
        nome='Auto no prazo',
        data_inicio=date(2026, 7, 1),
        data_fim=date(2026, 7, 21),
        status=Ciclo.Status.ABERTO,
        origem=Ciclo.Origem.AUTOMATICO,
        marco_competencia=date(2026, 7, 1),
    )
    Ciclo.objects.create(
        nome='Manual atrasado',
        data_inicio=date(2026, 5, 1),
        data_fim=date(2026, 5, 21),
        status=Ciclo.Status.ABERTO,
        origem=Ciclo.Origem.MANUAL,
        admitidos_ate=date(2026, 5, 1),
    )

    qs = ciclos_automaticos_em_atraso(ref_date=date(2026, 7, 10))
    assert list(qs) == [auto_atrasado]
