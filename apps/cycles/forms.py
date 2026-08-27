from django import forms

from apps.cycles.models import Ciclo

_INPUT = (
    'h-12 w-full rounded-lg border border-line bg-surface px-4 text-sm '
    'text-slate-800 shadow-sm transition-colors placeholder:text-slate-400 '
    'hover:border-slate-300 focus:border-transparent focus:outline-none '
    'focus:ring-2 focus:ring-emerald-500'
)


class CicloForm(forms.ModelForm):
    """Cadastro/edição de ciclo.

    No create, a view grava o ciclo e chama ``open_cycle`` (corte obrigatório).
    Na edição, só atualiza campos — não reabre nem rematricula.
    """

    class Meta:
        model = Ciclo
        fields = ('nome', 'data_inicio', 'data_fim', 'admitidos_ate')
        labels = {
            'nome': 'Nome do Ciclo',
            'data_inicio': 'Data de Início',
            'data_fim': 'Data de Encerramento',
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
        self.fields['nome'].widget.attrs.update(
            {
                'class': _INPUT,
                'placeholder': 'Ex: Avaliação Anual 2024',
            },
        )
        self.fields['admitidos_ate'].required = True
