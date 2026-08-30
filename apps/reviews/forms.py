from __future__ import annotations

from decimal import Decimal

from django import forms
from django.forms import BaseModelFormSet, modelformset_factory

from apps.accounts.services.scope import user_in_scope
from apps.cycles.models import Ciclo
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia, Feedback
from apps.reviews.services.evaluation import (
    MSG_AUTOAVALIACAO_INCOMPLETA,
    MSG_AUTOAVALIACAO_JA_ENVIADA,
    self_assessment_submitted,
    self_assessment_viewable,
)
from apps.reviews.widgets import ScaleRatingWidget

_DISCRETE_SCALE_MAX_OPTIONS = 10

_INPUT = (
    'w-full max-w-[8rem] rounded-lg border border-slate-200 px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent'
)

_TEXTAREA = (
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent'
)


def self_assessment_editable(avaliacao: Avaliacao | None) -> bool:
    """True se o colaborador pode registrar notas de autoavaliação."""
    if not self_assessment_viewable(avaliacao):
        return False
    return not self_assessment_submitted(avaliacao)


class SelfAssessmentForm(forms.ModelForm):
    """Nota de autoavaliação por competência (dentro da escala)."""

    class Meta:
        model = AvaliacaoCompetencia
        fields = ('nota_autoavaliacao',)
        labels = {
            'nota_autoavaliacao': 'Sua nota',
        }

    def __init__(self, *args, editable: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self._editable = editable
        escala = None
        if self.instance.pk and self.instance.competencia_id:
            competencia = getattr(self.instance, 'competencia', None)
            if competencia is not None:
                escala = getattr(competencia, 'escala', None)

        field = self.fields['nota_autoavaliacao']
        field.required = False

        if escala is not None:
            span = escala.valor_maximo - escala.valor_minimo
            if span < _DISCRETE_SCALE_MAX_OPTIONS:
                field.widget = ScaleRatingWidget(
                    min_value=escala.valor_minimo,
                    max_value=escala.valor_maximo,
                )
            else:
                attrs = {
                    'class': _INPUT,
                    'step': '0.01',
                    'inputmode': 'decimal',
                    'min': str(escala.valor_minimo),
                    'max': str(escala.valor_maximo),
                }
                field.widget.attrs.update(attrs)
        else:
            field.widget.attrs.update(
                {
                    'class': _INPUT,
                    'step': '0.01',
                    'inputmode': 'decimal',
                },
            )

        if not self._editable:
            field.disabled = True

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
            if self_assessment_submitted(avaliacao):
                raise forms.ValidationError(MSG_AUTOAVALIACAO_JA_ENVIADA)
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
    """True se a etapa/ciclo permitem avaliação do líder (sem ordem auto→líder)."""
    if avaliacao is None:
        return False
    if avaliacao.ciclo.status != Ciclo.Status.ABERTO:
        return False
    return avaliacao.etapa == Avaliacao.Etapa.AVALIACAO


def leader_assessment_permitted(avaliacao: Avaliacao | None) -> bool:
    """True se o líder pode registrar notas (etapa correta + autoavaliação enviada)."""
    return leader_assessment_editable(avaliacao) and self_assessment_submitted(
        avaliacao,
    )


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

        field = self.fields['nota_lider']
        field.required = False

        if escala is not None:
            span = escala.valor_maximo - escala.valor_minimo
            if span < _DISCRETE_SCALE_MAX_OPTIONS:
                field.widget = ScaleRatingWidget(
                    min_value=escala.valor_minimo,
                    max_value=escala.valor_maximo,
                    compact=True,
                    aria_label='Nota do líder',
                )
            else:
                attrs = {
                    'class': _INPUT,
                    'step': '0.01',
                    'inputmode': 'decimal',
                    'min': str(escala.valor_minimo),
                    'max': str(escala.valor_maximo),
                }
                field.widget.attrs.update(attrs)
        else:
            field.widget.attrs.update(
                {
                    'class': _INPUT,
                    'step': '0.01',
                    'inputmode': 'decimal',
                },
            )

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
        if not self_assessment_submitted(avaliacao):
            raise forms.ValidationError(MSG_AUTOAVALIACAO_INCOMPLETA)
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
            if not self_assessment_submitted(avaliacao):
                raise forms.ValidationError(MSG_AUTOAVALIACAO_INCOMPLETA)


LeaderAssessmentFormSet = modelformset_factory(
    AvaliacaoCompetencia,
    form=LeaderAssessmentForm,
    formset=BaseLeaderAssessmentFormSet,
    extra=0,
    can_delete=False,
)


def feedback_create_allowed(user, avaliacao: Avaliacao | None) -> bool:
    """True se o usuário pode registrar feedback nesta avaliação (ciclo aberto + escopo)."""
    if avaliacao is None or not getattr(user, 'pk', None):
        return False
    if avaliacao.ciclo.status != Ciclo.Status.ABERTO:
        return False
    return user_in_scope(user, avaliacao.usuario_id)


def resolve_feedback_tipo(autor, avaliacao: Avaliacao) -> str:
    """Colaborador na própria avaliação; líder (ou outro no escopo) caso contrário."""
    if getattr(autor, 'pk', None) == avaliacao.usuario_id:
        return Feedback.Tipo.COLABORADOR
    return Feedback.Tipo.LIDER


def can_acknowledge_feedback(user, feedback: Feedback) -> bool:
    """Ciência apenas do colaborador avaliado, em feedback do líder ainda sem ciente_em."""
    if feedback.tipo != Feedback.Tipo.LIDER:
        return False
    if feedback.ciente_em is not None:
        return False
    return feedback.avaliacao.usuario_id == getattr(user, 'pk', None)


_FEEDBACK_TEXTAREA = (
    'w-full min-h-[160px] resize-y rounded-lg border border-slate-200 bg-slate-50 '
    'px-4 py-4 text-sm text-ink focus:border-transparent focus:bg-white '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500'
)


def feedback_destinatario(avaliacao: Avaliacao, autor) -> tuple:
    """Pessoa exibida no cartão contextual e rótulo do campo.

    Líder registra feedback *para* o liderado; colaborador registra *para* o gestor
    (contraparte da conversa de feedback). Sem gestor definido, cai no colaborador.
    """
    colaborador = avaliacao.usuario
    if getattr(autor, 'pk', None) == colaborador.pk:
        gestor = getattr(colaborador, 'line_manager', None)
        if gestor is not None:
            return gestor, 'Para'
        return colaborador, 'Colaborador'
    return colaborador, 'Para'


class FeedbackForm(forms.ModelForm):
    """Conteúdo estruturado do feedback (tipo/autor definidos na view)."""

    class Meta:
        model = Feedback
        fields = ('conteudo',)
        labels = {
            'conteudo': 'Conteúdo do Feedback',
        }
        widgets = {
            'conteudo': forms.Textarea(
                attrs={
                    'class': _FEEDBACK_TEXTAREA,
                    'rows': 8,
                    'placeholder': 'Descreva o feedback de forma clara e objetiva...',
                },
            ),
        }

    def __init__(self, *args, avaliacao: Avaliacao | None = None, **kwargs):
        self.avaliacao = avaliacao
        super().__init__(*args, **kwargs)
        self.fields['conteudo'].required = True

    def clean_conteudo(self):
        conteudo = (self.cleaned_data.get('conteudo') or '').strip()
        if not conteudo:
            raise forms.ValidationError('Informe o conteúdo do feedback.')
        return conteudo

    def clean(self):
        cleaned = super().clean()
        if self.avaliacao is not None and self.avaliacao.ciclo.status != Ciclo.Status.ABERTO:
            raise forms.ValidationError(
                'Só é possível registrar feedback em um ciclo aberto.',
            )
        return cleaned
