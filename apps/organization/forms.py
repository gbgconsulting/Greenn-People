from django import forms

from apps.accounts.models import CustomUser
from apps.organization.models import Area, Cargo

_INPUT = (
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent'
)
_CHECKBOX = 'h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500'


class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ('nome', 'parent', 'is_active')
        labels = {
            'nome': 'Nome',
            'parent': 'Área pai',
            'is_active': 'Ativa',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].widget.attrs.update({'class': _INPUT})
        self.fields['parent'].widget.attrs.update({'class': _INPUT})
        self.fields['is_active'].widget.attrs.update({'class': _CHECKBOX})
        qs = Area.objects.filter(is_active=True).order_by('nome')
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        self.fields['parent'].queryset = qs
        self.fields['parent'].required = False
        self.fields['parent'].empty_label = '— Nenhuma —'


class CargoForm(forms.ModelForm):
    class Meta:
        model = Cargo
        fields = ('nome', 'nivel', 'is_active')
        labels = {
            'nome': 'Nome',
            'nivel': 'Nível',
            'is_active': 'Ativo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].widget.attrs.update({'class': _INPUT})
        self.fields['nivel'].widget.attrs.update({'class': _INPUT, 'min': '1'})
        self.fields['is_active'].widget.attrs.update({'class': _CHECKBOX})


class UserUpdateForm(forms.ModelForm):
    """Admin edit of organizational links and flags (RF-04 / Sprint 2.4.3)."""

    class Meta:
        model = CustomUser
        fields = (
            'nome',
            'area',
            'cargo',
            'line_manager',
            'is_admin',
            'is_active',
            'data_entrada',
        )
        labels = {
            'nome': 'Nome',
            'area': 'Área',
            'cargo': 'Cargo',
            'line_manager': 'Gestor direto',
            'is_admin': 'Administrador',
            'is_active': 'Ativo',
            'data_entrada': 'Data de entrada',
        }
        widgets = {
            'data_entrada': forms.DateInput(
                attrs={'type': 'date', 'class': _INPUT},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('nome', 'area', 'cargo', 'line_manager'):
            self.fields[name].widget.attrs.update({'class': _INPUT})
        for name in ('is_admin', 'is_active'):
            self.fields[name].widget.attrs.update({'class': _CHECKBOX})

        self.fields['area'].queryset = Area.objects.filter(
            is_active=True,
        ).order_by('nome')
        self.fields['area'].required = False
        self.fields['area'].empty_label = '— Sem área —'

        self.fields['cargo'].queryset = Cargo.objects.filter(
            is_active=True,
        ).order_by('nivel', 'nome')
        self.fields['cargo'].required = False
        self.fields['cargo'].empty_label = '— Sem cargo —'

        managers = CustomUser.objects.filter(is_active=True).order_by('nome')
        if self.instance.pk:
            managers = managers.exclude(pk=self.instance.pk)
        self.fields['line_manager'].queryset = managers
        self.fields['line_manager'].required = False
        self.fields['line_manager'].empty_label = '— Sem gestor —'
