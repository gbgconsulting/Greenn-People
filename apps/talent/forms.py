from __future__ import annotations

from django import forms

from apps.cycles.models import Ciclo
from apps.goals.forms import get_open_ciclo

_INPUT = (
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent'
)

_POTENCIAL_CHOICES = (
    (1, '1 — Baixo'),
    (2, '2 — Médio'),
    (3, '3 — Alto'),
)


class ClassificacaoForm(forms.Form):
    """Formulário admin para definir potencial (1–3) no ciclo (RF-24)."""

    ciclo = forms.ModelChoiceField(
        queryset=Ciclo.objects.none(),
        label='Ciclo',
        empty_label=None,
    )
    potencial = forms.TypedChoiceField(
        choices=_POTENCIAL_CHOICES,
        coerce=int,
        label='Potencial',
        help_text='Definido manualmente pelo administrador. O desempenho é derivado da nota do líder.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ciclo'].queryset = Ciclo.objects.order_by('-data_inicio', 'nome')
        self.fields['ciclo'].widget.attrs.update({'class': _INPUT})
        self.fields['potencial'].widget.attrs.update({'class': _INPUT})

        if not self.is_bound and not self.initial.get('ciclo'):
            aberto = get_open_ciclo()
            if aberto is not None:
                self.fields['ciclo'].initial = aberto.pk
