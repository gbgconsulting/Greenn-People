from __future__ import annotations

from django import forms

from apps.accounts.services.scope import get_visible_users, user_in_scope
from apps.pdi.models import PDI

_INPUT = (
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent'
)
_SELECT = (
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent bg-white'
)


class PDIForm(forms.ModelForm):
    """Cadastro de PDI; ``usuario`` restrito ao escopo do solicitante."""

    class Meta:
        model = PDI
        fields = ('usuario', 'titulo', 'status')
        labels = {
            'usuario': 'Colaborador',
            'titulo': 'Título',
            'status': 'Status',
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        self.fields['titulo'].widget.attrs.update({'class': _INPUT})
        self.fields['status'].widget.attrs.update({'class': _SELECT})

        visible = get_visible_users(user) if user is not None else None
        if visible is not None:
            self.fields['usuario'].queryset = visible.order_by('nome', 'email')
            self.fields['usuario'].widget.attrs.update({'class': _SELECT})
            self.fields['usuario'].label_from_instance = (
                lambda u: u.nome or u.email
            )
            if not getattr(user, 'is_leader', False) and not getattr(
                user, 'is_manager', False,
            ) and not getattr(user, 'is_admin', False):
                self.fields['usuario'].initial = user.pk
                self.fields['usuario'].widget = forms.HiddenInput()
            else:
                self.fields['usuario'].initial = user.pk
        else:
            from apps.accounts.models import CustomUser

            self.fields['usuario'].queryset = CustomUser.objects.none()

    def clean_usuario(self):
        usuario = self.cleaned_data['usuario']
        if self.user is None or not user_in_scope(self.user, usuario.pk):
            raise forms.ValidationError(
                'Você não tem permissão para criar PDI para este colaborador.',
            )
        return usuario
