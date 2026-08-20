from django import forms

from apps.cycles.models import Ciclo

_INPUT = (
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent'
)

_INPUT_COMPACT = (
    'rounded-lg border border-slate-200 px-2 py-1 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent'
)


class CicloOpenForm(forms.Form):
    """Campo de corte no POST de Abrir; gate permanece em ``open_cycle``."""

    admitidos_ate = forms.DateField(
        label='Admitidos até',
        required=False,
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': _INPUT_COMPACT},
        ),
    )


class CicloForm(forms.ModelForm):
    """Cadastro/edição de ciclo; status é controlado por abrir/encerrar.

    ``admitidos_ate`` é opcional no save (pré-preencher); a obrigação
    de corte vale só em ``open_cycle``.
    """

    class Meta:
        model = Ciclo
        fields = ('nome', 'data_inicio', 'data_fim', 'admitidos_ate')
        labels = {
            'nome': 'Nome',
            'data_inicio': 'Data de início',
            'data_fim': 'Data de fim',
            'admitidos_ate': 'Admitidos até',
        }
        help_texts = {
            'data_fim': 'Informativo; o encerramento do ciclo é manual.',
            'admitidos_ate': (
                'Opcional no cadastro; obrigatório ao abrir o ciclo.'
            ),
        }
        widgets = {
            'data_inicio': forms.DateInput(
                attrs={'type': 'date', 'class': _INPUT},
            ),
            'data_fim': forms.DateInput(
                attrs={'type': 'date', 'class': _INPUT},
            ),
            'admitidos_ate': forms.DateInput(
                attrs={'type': 'date', 'class': _INPUT},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].widget.attrs.update({'class': _INPUT})
        self.fields['admitidos_ate'].required = False

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get('data_inicio')
        fim = cleaned.get('data_fim')
        if inicio and fim and fim < inicio:
            self.add_error(
                'data_fim',
                'A data de fim deve ser igual ou posterior à data de início.',
            )
        return cleaned
