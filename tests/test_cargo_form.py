"""Validação de ``CargoForm`` (nível 1–6)."""

from __future__ import annotations

import pytest

from apps.organization.forms import CargoForm
from apps.organization.models import Cargo


@pytest.mark.django_db
def test_cargo_form_create_rejeita_nivel_fora_do_intervalo():
    form = CargoForm(
        data={
            'nome': 'Cargo inválido',
            'nivel': '100',
            'is_active': True,
        },
    )

    assert not form.is_valid()
    assert 'nivel' in form.errors


@pytest.mark.django_db
def test_cargo_form_create_aceita_niveis_canonicos():
    form = CargoForm(
        data={
            'nome': 'Analista Pleno',
            'nivel': '3',
            'is_active': True,
        },
    )

    assert form.is_valid(), form.errors
    cargo = form.save()
    assert cargo.nivel == 3


@pytest.mark.django_db
def test_cargo_form_create_exige_nivel():
    form = CargoForm(
        data={
            'nome': 'Sem nível',
            'nivel': '',
            'is_active': True,
        },
    )

    assert not form.is_valid()
    assert 'nivel' in form.errors


@pytest.mark.django_db
def test_cargo_form_edit_rejeita_nivel_invalido_legado():
    cargo = Cargo.objects.create(nome='Cargo legado', nivel=100)

    form = CargoForm(
        data={
            'nome': cargo.nome,
            'nivel': '100',
            'is_active': True,
        },
        instance=cargo,
    )

    assert not form.is_valid()
    assert 'nivel' in form.errors


@pytest.mark.django_db
def test_cargo_form_oferece_opcoes_de_nivel():
    form = CargoForm()
    values = {choice[0] for choice in form.fields['nivel'].choices if choice[0] != ''}

    assert values == {1, 2, 3, 4, 5, 6}
