import json
from decimal import Decimal

from django import forms
from django.forms import inlineformset_factory

from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.organization.models import Cargo

_INPUT = (
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent'
)
_TEXTAREA = (
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm font-mono '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent'
)
_CHECKBOX = 'h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500'


class EscalaForm(forms.ModelForm):
    rotulos_texto = forms.CharField(
        label='Rótulos por nível (JSON)',
        required=False,
        widget=forms.Textarea(
            attrs={
                'class': _TEXTAREA,
                'rows': 4,
                'placeholder': '{"1": "Iniciante", "5": "Expert"}',
            },
        ),
        help_text=(
            'Mapa nível → rótulo em JSON. Ex.: '
            '{"1": "Iniciante", "3": "Pleno", "5": "Expert"}.'
        ),
    )

    class Meta:
        model = Escala
        fields = ('nome', 'valor_minimo', 'valor_maximo', 'is_active')
        labels = {
            'nome': 'Nome',
            'valor_minimo': 'Valor mínimo',
            'valor_maximo': 'Valor máximo',
            'is_active': 'Ativa',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].widget.attrs.update({'class': _INPUT})
        self.fields['valor_minimo'].widget.attrs.update({'class': _INPUT})
        self.fields['valor_maximo'].widget.attrs.update({'class': _INPUT})
        self.fields['is_active'].widget.attrs.update({'class': _CHECKBOX})
        if self.instance.pk and self.instance.rotulos_por_nivel:
            self.fields['rotulos_texto'].initial = json.dumps(
                self.instance.rotulos_por_nivel,
                ensure_ascii=False,
                indent=2,
            )

    def clean_rotulos_texto(self):
        raw = (self.cleaned_data.get('rotulos_texto') or '').strip()
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(
                'JSON inválido. Use o formato {"1": "rótulo", ...}.',
            ) from exc
        if not isinstance(data, dict):
            raise forms.ValidationError(
                'Os rótulos devem ser um objeto JSON (mapa nível → rótulo).',
            )
        normalized = {}
        for key, value in data.items():
            normalized[str(key)] = str(value)
        return normalized

    def clean(self):
        cleaned = super().clean()
        minimo = cleaned.get('valor_minimo')
        maximo = cleaned.get('valor_maximo')
        if minimo is not None and maximo is not None and maximo <= minimo:
            self.add_error(
                'valor_maximo',
                'O valor máximo deve ser maior que o valor mínimo.',
            )
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.rotulos_por_nivel = self.cleaned_data.get('rotulos_texto') or {}
        if commit:
            instance.save()
        return instance


class CompetenciaForm(forms.ModelForm):
    class Meta:
        model = Competencia
        fields = ('nome', 'descricao', 'tipo', 'escala', 'is_active')
        labels = {
            'nome': 'Nome',
            'descricao': 'Descrição',
            'tipo': 'Tipo',
            'escala': 'Escala',
            'is_active': 'Ativa',
        }
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3, 'class': _INPUT}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('nome', 'tipo', 'escala'):
            self.fields[name].widget.attrs.update({'class': _INPUT})
        self.fields['is_active'].widget.attrs.update({'class': _CHECKBOX})
        self.fields['escala'].queryset = Escala.objects.filter(
            is_active=True,
        ).order_by('nome')
        self.fields['descricao'].required = False


class CargoCompetenciaForm(forms.ModelForm):
    class Meta:
        model = CargoCompetencia
        fields = ('competencia', 'nivel_esperado', 'peso')
        labels = {
            'competencia': 'Competência',
            'nivel_esperado': 'Nível esperado',
            'peso': 'Peso',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('competencia', 'nivel_esperado', 'peso'):
            self.fields[name].widget.attrs.update({'class': _INPUT})
        self.fields['competencia'].queryset = Competencia.objects.filter(
            is_active=True,
        ).select_related('escala').order_by('nome')
        self.fields['peso'].widget.attrs.update({'min': '0.01', 'step': '0.01'})
        self.fields['nivel_esperado'].widget.attrs.update({'step': '0.01'})

    def clean_peso(self):
        peso = self.cleaned_data.get('peso')
        if peso is not None and peso <= Decimal('0'):
            raise forms.ValidationError('O peso deve ser maior que zero.')
        return peso


CargoCompetenciaFormSet = inlineformset_factory(
    Cargo,
    CargoCompetencia,
    form=CargoCompetenciaForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)
