"""Seletores create vs edit com soft-delete (T047 / catalog-offboarding-contract)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.competencies.forms import CargoCompetenciaForm, CompetenciaForm
from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.organization.forms import AreaForm, UserUpdateForm
from apps.organization.models import Area, Cargo


@pytest.fixture
def escala_ativa(db) -> Escala:
    return Escala.objects.create(
        nome='Escala Ativa',
        valor_minimo=1,
        valor_maximo=5,
    )


@pytest.fixture
def escala_inativa(db) -> Escala:
    return Escala.objects.create(
        nome='Escala Inativa',
        valor_minimo=1,
        valor_maximo=5,
        is_active=False,
    )


@pytest.mark.django_db
def test_competencia_form_create_nao_lista_escala_inativa(
    escala_ativa,
    escala_inativa,
):
    form = CompetenciaForm()
    pks = set(form.fields['escala'].queryset.values_list('pk', flat=True))

    assert escala_ativa.pk in pks
    assert escala_inativa.pk not in pks


@pytest.mark.django_db
def test_competencia_form_edit_preserva_escala_inativa(
    escala_ativa,
    escala_inativa,
):
    competencia = Competencia.objects.create(
        nome='Competência com escala inativa',
        tipo=Competencia.Tipo.TECNICA,
        escala=escala_inativa,
    )

    form = CompetenciaForm(instance=competencia)
    pks = set(form.fields['escala'].queryset.values_list('pk', flat=True))
    assert escala_inativa.pk in pks
    assert escala_ativa.pk in pks

    bound = CompetenciaForm(
        data={
            'nome': competencia.nome,
            'descricao': '',
            'tipo': competencia.tipo,
            'escala': escala_inativa.pk,
            'is_active': True,
        },
        instance=competencia,
    )
    assert bound.is_valid(), bound.errors
    saved = bound.save()
    assert saved.escala_id == escala_inativa.pk


@pytest.mark.django_db
def test_cargo_competencia_form_edit_preserva_competencia_inativa(
    escala_ativa,
    cargo_colab,
):
    competencia = Competencia.objects.create(
        nome='Competência inativa',
        tipo=Competencia.Tipo.COMPORTAMENTAL,
        escala=escala_ativa,
        is_active=False,
    )
    vinculo = CargoCompetencia.objects.create(
        cargo=cargo_colab,
        competencia=competencia,
        nivel_esperado=Decimal('3.00'),
        peso=Decimal('1.00'),
    )

    form = CargoCompetenciaForm(instance=vinculo)
    pks = set(form.fields['competencia'].queryset.values_list('pk', flat=True))
    assert competencia.pk in pks

    create_form = CargoCompetenciaForm()
    create_pks = set(
        create_form.fields['competencia'].queryset.values_list('pk', flat=True),
    )
    assert competencia.pk not in create_pks


@pytest.mark.django_db
def test_user_update_form_preserva_area_e_cargo_inativos(
    colaborador,
    area,
    cargo_colab,
):
    area.is_active = False
    area.save(update_fields=['is_active', 'updated_at'])
    cargo_colab.is_active = False
    cargo_colab.save(update_fields=['is_active', 'updated_at'])

    form = UserUpdateForm(instance=colaborador)
    assert area.pk in form.fields['area'].queryset.values_list('pk', flat=True)
    assert cargo_colab.pk in form.fields['cargo'].queryset.values_list(
        'pk',
        flat=True,
    )


@pytest.mark.django_db
def test_area_form_edit_preserva_parent_inativo(db):
    parent = Area.objects.create(nome='Pai Inativo', is_active=False)
    child = Area.objects.create(nome='Filha', parent=parent)

    form = AreaForm(instance=child)
    pks = set(form.fields['parent'].queryset.values_list('pk', flat=True))
    assert parent.pk in pks
    assert child.pk not in pks
