from __future__ import annotations

from decimal import Decimal

from django import forms
from django.forms import BaseModelFormSet, modelformset_factory

from apps.cycles.models import Ciclo
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia

_INPUT = (
    'w-full max-w-[8rem] rounded-lg border border-slate-200 px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent'
)


def self_assessment_editable(avaliacao: Avaliacao | None) -> bool:
    """True se o colaborador pode registrar notas de autoavaliação."""
    if avaliacao is None:
        return False
    if avaliacao.ciclo.status != Ciclo.Status.ABERTO:
        return False
    return avaliacao.etapa == Avaliacao.Etapa.AVALIACAO


class SelfAssessmentForm(forms.ModelForm):
    """Nota de autoavaliação por competência (dentro da escala)."""

    class Meta:
        model = AvaliacaoCompetencia
        fields = ('nota_autoavaliacao',)
        labels = {
            'nota_autoavaliacao': 'Sua nota',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        escala = None
        if self.instance.pk and self.instance.competencia_id:
            competencia = getattr(self.instance, 'competencia', None)
            if competencia is not None:
                escala = getattr(competencia, 'escala', None)

        attrs = {
            'class': _INPUT,
            'step': '0.01',
            'inputmode': 'decimal',
        }
        if escala is not None:
            attrs['min'] = str(escala.valor_minimo)
            attrs['max'] = str(escala.valor_maximo)
        self.fields['nota_autoavaliacao'].widget.attrs.update(attrs)
        self.fields['nota_autoavaliacao'].required = False

    def clean_nota_autoavaliacao(self):
        nota = self.cleaned_data.get('nota_autoavaliacao')
        if nota is None:
            return nota

        competencia = self.instance.competencia
        escala = competencia.escala
        minimo = Decimal(escala.valor_minimo)
        maximo = Decimal(escala.valor_maximo)
        if nota < minimo or nota > maximo:
            raise forms.ValidationError(
                f'A nota deve estar entre {escala.valor_minimo} e '
                f'{escala.valor_maximo} (escala {escala.nome}).',
            )
        return nota

    def clean(self):
        cleaned = super().clean()
        avaliacao = self.instance.avaliacao if self.instance.pk else None
        if not self_assessment_editable(avaliacao):
            raise forms.ValidationError(
                'A autoavaliação só pode ser registrada na etapa de avaliação '
                'de um ciclo aberto.',
            )
        return cleaned


class BaseSelfAssessmentFormSet(BaseModelFormSet):
    """Formset das linhas de competência da avaliação do colaborador."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or form.cleaned_data is None:
                continue
            if form.cleaned_data.get('DELETE'):
                continue
            avaliacao = form.instance.avaliacao if form.instance.pk else None
            if not self_assessment_editable(avaliacao):
                raise forms.ValidationError(
                    'A autoavaliação só pode ser registrada na etapa de '
                    'avaliação de um ciclo aberto.',
                )


SelfAssessmentFormSet = modelformset_factory(
    AvaliacaoCompetencia,
    form=SelfAssessmentForm,
    formset=BaseSelfAssessmentFormSet,
    extra=0,
    can_delete=False,
)


def leader_assessment_editable(avaliacao: Avaliacao | None) -> bool:
    """True se o líder pode registrar notas na etapa de avaliação."""
    if avaliacao is None:
        return False
    if avaliacao.ciclo.status != Ciclo.Status.ABERTO:
        return False
    return avaliacao.etapa == Avaliacao.Etapa.AVALIACAO


def can_leader_assess(assessor, avaliacao: Avaliacao) -> bool:
    """True se ``assessor`` é o gestor direto (ou admin se sem gestor).

    O próprio avaliado nunca avalia como líder (usa autoavaliação).
    """
    if avaliacao.usuario_id == getattr(assessor, 'pk', None):
        return False
    manager_id = avaliacao.usuario.line_manager_id
    if manager_id is None:
        return bool(getattr(assessor, 'is_admin', False))
    return getattr(assessor, 'pk', None) == manager_id


class LeaderAssessmentForm(forms.ModelForm):
    """Nota do líder por competência, com comparação ao nível esperado (snapshot)."""

    class Meta:
        model = AvaliacaoCompetencia
        fields = ('nota_lider',)
        labels = {
            'nota_lider': 'Nota do líder',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        escala = None
        if self.instance.pk and self.instance.competencia_id:
            competencia = getattr(self.instance, 'competencia', None)
            if competencia is not None:
                escala = getattr(competencia, 'escala', None)

        attrs = {
            'class': _INPUT,
            'step': '0.01',
            'inputmode': 'decimal',
        }
        if escala is not None:
            attrs['min'] = str(escala.valor_minimo)
            attrs['max'] = str(escala.valor_maximo)
        self.fields['nota_lider'].widget.attrs.update(attrs)
        self.fields['nota_lider'].required = False

    @property
    def comparacao_nivel(self) -> str:
        """Relação da nota do líder com ``nivel_esperado_utilizado`` (UI)."""
        nota = self.instance.nota_lider
        if nota is None and hasattr(self, 'cleaned_data'):
            nota = self.cleaned_data.get('nota_lider')
        if nota is None:
            return ''
        esperado = Decimal(self.instance.nivel_esperado_utilizado)
        if nota > esperado:
            return 'acima'
        if nota < esperado:
            return 'abaixo'
        return 'igual'

    def clean_nota_lider(self):
        nota = self.cleaned_data.get('nota_lider')
        if nota is None:
            return nota

        competencia = self.instance.competencia
        escala = competencia.escala
        minimo = Decimal(escala.valor_minimo)
        maximo = Decimal(escala.valor_maximo)
        if nota < minimo or nota > maximo:
            raise forms.ValidationError(
                f'A nota deve estar entre {escala.valor_minimo} e '
                f'{escala.valor_maximo} (escala {escala.nome}).',
            )
        return nota

    def clean(self):
        cleaned = super().clean()
        avaliacao = self.instance.avaliacao if self.instance.pk else None
        if not leader_assessment_editable(avaliacao):
            raise forms.ValidationError(
                'A avaliação do líder só pode ser registrada na etapa de '
                'avaliação de um ciclo aberto.',
            )
        return cleaned


class BaseLeaderAssessmentFormSet(BaseModelFormSet):
    """Formset das linhas de competência para avaliação do líder."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        for form in self.forms:
            if not hasattr(form, 'cleaned_data') or form.cleaned_data is None:
                continue
            if form.cleaned_data.get('DELETE'):
                continue
            avaliacao = form.instance.avaliacao if form.instance.pk else None
            if not leader_assessment_editable(avaliacao):
                raise forms.ValidationError(
                    'A avaliação do líder só pode ser registrada na etapa de '
                    'avaliação de um ciclo aberto.',
                )


LeaderAssessmentFormSet = modelformset_factory(
    AvaliacaoCompetencia,
    form=LeaderAssessmentForm,
    formset=BaseLeaderAssessmentFormSet,
    extra=0,
    can_delete=False,
)
