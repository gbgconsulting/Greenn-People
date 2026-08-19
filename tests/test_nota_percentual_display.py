"""Exibição de nota final normalizada como percentual (paridade com gráficos)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.template import Context, Template
from django.test import Client
from django.urls import reverse

from apps.reviews.services.display import format_nota_percentual
from tests.conftest import DEFAULT_PASSWORD


def test_format_nota_percentual_075_vira_75_porcento():
    assert format_nota_percentual(Decimal('0.7500')) == '75%'


def test_format_nota_percentual_arredonda_half_up():
    assert format_nota_percentual(Decimal('0.3333')) == '33%'
    assert format_nota_percentual(Decimal('0.3350')) == '34%'
    assert format_nota_percentual(Decimal('1.0000')) == '100%'
    assert format_nota_percentual(Decimal('0')) == '0%'


def test_format_nota_percentual_ausente():
    assert format_nota_percentual(None) == '—'
    assert format_nota_percentual('') == '—'


def test_filtro_template_nota_percentual():
    html = Template(
        '{% load review_display %}{{ nota|nota_percentual }}',
    ).render(Context({'nota': Decimal('0.7500')}))
    assert html == '75%'


@pytest.mark.django_db
def test_avaliacao_detail_mostra_nota_final_em_percentual(admin, avaliacao):
    avaliacao.nota_final_lider = Decimal('0.7500')
    avaliacao.nota_final_autoavaliacao = Decimal('0.5000')
    avaliacao.save(
        update_fields=['nota_final_lider', 'nota_final_autoavaliacao'],
    )
    client = Client()
    client.login(email=admin.email, password=DEFAULT_PASSWORD)
    resp = client.get(reverse('reviews:detail', kwargs={'pk': avaliacao.pk}))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert '75%' in body
    assert '50%' in body
    assert '0.7500' not in body
    assert '0,7500' not in body
