from django import forms

from apps.cycles.models import Ciclo

_INPUT = (
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent'
)


class CicloForm(forms.ModelForm):
    """Cadastro/edição de ciclo; status é controlado por abrir/encerrar.

    ``admitidos_ate`` é definido aqui e reutilizado na abertura
    (``open_cycle`` lê o valor já persistido).
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
            'data_fim': '',
            'admitidos_ate': '',
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
        self.fields['admitidos_ate'].required = True

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
