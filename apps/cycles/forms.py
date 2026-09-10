from django import forms
from django.utils import timezone

from apps.cycles.models import Ciclo

_INPUT = (
    'h-12 w-full rounded-lg border border-line bg-surface px-4 text-sm '
    'text-slate-800 shadow-sm transition-colors placeholder:text-slate-400 '
    'hover:border-slate-300 focus:border-transparent focus:outline-none '
    'focus:ring-2 focus:ring-emerald-500'
)

_SELECT = (
    'h-12 w-full rounded-lg border border-line bg-surface px-4 text-sm '
    'text-slate-800 shadow-sm transition-colors hover:border-slate-300 '
    'focus:border-transparent focus:outline-none focus:ring-2 '
    'focus:ring-emerald-500'
)

_MESES = (
    (1, 'Janeiro'),
    (2, 'Fevereiro'),
    (3, 'Março'),
    (4, 'Abril'),
    (5, 'Maio'),
    (6, 'Junho'),
    (7, 'Julho'),
    (8, 'Agosto'),
    (9, 'Setembro'),
    (10, 'Outubro'),
    (11, 'Novembro'),
    (12, 'Dezembro'),
)


class GovernancePeriodFilterForm(forms.Form):
    """Filtro GET leve do período da governança automática (US4 / T023).

    Query inválida ou incompleta → mês civil atual (não 400).
    **Não** dispara lote nem altera estado — só lê.
    """

    year = forms.IntegerField(
        required=False,
        min_value=2000,
        max_value=2100,
        label='Ano',
        widget=forms.NumberInput(attrs={'class': _INPUT, 'placeholder': 'Ano'}),
    )
    month = forms.TypedChoiceField(
        required=False,
        coerce=int,
        choices=[('', 'Mês atual')] + list(_MESES),
        empty_value=None,
        label='Mês',
        widget=forms.Select(attrs={'class': _SELECT}),
    )

    @classmethod
    def from_request_get(cls, data) -> 'GovernancePeriodFilterForm':
        """Instancia e valida; sempre devolve form com ``cleaned_data`` seguro."""
        form = cls(data)
        form.is_valid()
        return form

    def resolved_year_month(self) -> tuple[int, int]:
        """Resolve ``(ano, mês)`` para o snapshot; default = mês civil de hoje."""
        today = timezone.localdate()
        cleaned = getattr(self, 'cleaned_data', None) or {}
        year = cleaned.get('year')
        month = cleaned.get('month')
        if year is None or month is None:
            return today.year, today.month
        return int(year), int(month)


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
