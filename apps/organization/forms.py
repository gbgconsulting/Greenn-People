from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models import CustomUser
from apps.core.forms import active_choices_queryset
from apps.organization.models import Area, Cargo
from apps.reviews.services.enrollment import ensure_avaliacao_for_user

_INPUT = (
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent'
)
_CHECKBOX = 'h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500'


class ReassignDirectReportsForm(forms.Form):
    """Seleciona o novo gestor para reatribuição em lote dos liderados ativos."""

    to_manager = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),
        label='Novo gestor',
        empty_label='— Selecione o novo gestor —',
    )

    def __init__(self, *args, from_manager=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.from_manager = from_manager
        managers = CustomUser.objects.filter(is_active=True).order_by('nome')
        if from_manager is not None and from_manager.pk:
            managers = managers.exclude(pk=from_manager.pk)
        self.fields['to_manager'].queryset = managers
        self.fields['to_manager'].widget.attrs.update({'class': _INPUT})


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
        current_parent_id = (
            self.instance.parent_id if self.instance.pk else None
        )
        qs = active_choices_queryset(
            Area.objects.all(),
            current_pk=current_parent_id,
        ).order_by('nome')
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
        self._was_active = bool(self.instance.pk and self.instance.is_active)
        for name in ('nome', 'area', 'cargo', 'line_manager'):
            self.fields[name].widget.attrs.update({'class': _INPUT})
        for name in ('is_admin', 'is_active'):
            self.fields[name].widget.attrs.update({'class': _CHECKBOX})

        current_area_id = self.instance.area_id if self.instance.pk else None
        self.fields['area'].queryset = active_choices_queryset(
            Area.objects.all(),
            current_pk=current_area_id,
        ).order_by('nome')
        self.fields['area'].required = False
        self.fields['area'].empty_label = '— Sem área —'

        current_cargo_id = self.instance.cargo_id if self.instance.pk else None
        self.fields['cargo'].queryset = active_choices_queryset(
            Cargo.objects.all(),
            current_pk=current_cargo_id,
        ).order_by('nivel', 'nome')
        self.fields['cargo'].required = False
        self.fields['cargo'].empty_label = '— Sem cargo —'

        current_manager_id = (
            self.instance.line_manager_id if self.instance.pk else None
        )
        managers = active_choices_queryset(
            CustomUser.objects.all(),
            current_pk=current_manager_id,
        ).order_by('nome')
        if self.instance.pk:
            managers = managers.exclude(pk=self.instance.pk)
        self.fields['line_manager'].queryset = managers
        self.fields['line_manager'].required = False
        self.fields['line_manager'].empty_label = '— Sem gestor —'

    def clean(self):
        cleaned = super().clean()
        # Surface FR-028 on the form before save (ModelForm already runs
        # instance.clean via _post_clean; keep explicit check for clarity).
        if cleaned.get('is_active') is False and self.instance.pk:
            if self.instance.has_active_direct_reports():
                raise ValidationError(
                    {
                        'is_active': (
                            'Não é possível desativar um colaborador que ainda '
                            'possui liderados ativos. Reatribua-os antes.'
                        ),
                    },
                )
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and user.is_active and not self._was_active:
            transaction.on_commit(
                lambda u=user: ensure_avaliacao_for_user(u),
            )
        return user
