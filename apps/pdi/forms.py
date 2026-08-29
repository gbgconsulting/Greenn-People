from __future__ import annotations

from django import forms
from django.utils import timezone

from apps.accounts.services.scope import get_visible_users, user_in_scope
from apps.pdi.models import AcaoPDI, PDI

_INPUT = (
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent'
)
_PDI_INPUT = (
    'w-full rounded-lg border-none bg-slate-50 p-4 font-ui text-base '
    'text-slate-800 transition-colors placeholder:text-slate-400 '
    'focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500'
)
_PDI_SELECT = (
    'w-full appearance-none rounded-lg border-none bg-slate-50 py-3 pl-10 '
    'pr-10 font-ui text-base text-slate-800 transition-colors '
    'focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500'
)
_SELECT = (
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent bg-white'
)
_TEXTAREA = (
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent min-h-[5rem]'
)
_ACAO_FIELD = (
    'w-full rounded-lg border border-transparent bg-slate-50 px-4 py-3 '
    'font-ui text-base text-slate-800 transition-colors duration-200 '
    'placeholder:text-slate-400 focus:border-2 focus:border-emerald-800 '
    'focus:bg-white focus:outline-none focus:ring-0'
)
_ACAO_TEXTAREA = f'{_ACAO_FIELD} resize-none min-h-[6rem]'


class PDIForm(forms.ModelForm):
    """Cadastro de PDI; ``usuario`` restrito ao escopo do solicitante."""

    class Meta:
        model = PDI
        fields = ('usuario', 'titulo')
        labels = {
            'usuario': 'Colaborador',
            'titulo': 'Título do PDI',
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

        self.fields['titulo'].widget.attrs.update(
            {
                'class': _PDI_INPUT,
                'placeholder': (
                    'Ex: Ciclo de Liderança 2024 ou Especialização Técnica Q3'
                ),
            },
        )

        visible = get_visible_users(user) if user is not None else None
        if visible is not None:
            self.fields['usuario'].queryset = visible.order_by('nome', 'email')
            self.fields['usuario'].widget.attrs.update({'class': _PDI_SELECT})
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
                self.fields['usuario'].empty_label = (
                    'Selecione o colaborador...'
                )
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


class AcaoPDIForm(forms.ModelForm):
    """Criação/edição de ação de PDI; ``prazo`` >= hoje apenas na criação."""

    titulo_acao = forms.CharField(
        label='Título da Ação',
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Ex: Curso de Liderança Avançada',
            },
        ),
    )

    class Meta:
        model = AcaoPDI
        fields = ('descricao', 'responsavel', 'prazo')
        labels = {
            'descricao': 'Descrição e Objetivos',
            'responsavel': 'Responsável',
            'prazo': 'Prazo Estimado',
        }
        widgets = {
            'descricao': forms.Textarea(
                attrs={
                    'rows': 4,
                    'placeholder': (
                        'Descreva os objetivos que você espera alcançar '
                        'com esta ação...'
                    ),
                },
            ),
            'prazo': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date'},
            ),
        }

    def __init__(self, *args, user=None, pdi: PDI | None = None, **kwargs):
        self.user = user
        self.pdi = pdi
        super().__init__(*args, **kwargs)

        is_create = not self.instance.pk

        if is_create:
            self.fields['titulo_acao'].required = True
            self.fields['descricao'].required = False
            self.fields['titulo_acao'].widget.attrs.update({'class': _ACAO_FIELD})
            self.fields['descricao'].widget.attrs.update({'class': _ACAO_TEXTAREA})
            self.fields['prazo'].widget.attrs.update({'class': _ACAO_FIELD})
            self.fields['responsavel'].widget = forms.HiddenInput()
        else:
            del self.fields['titulo_acao']
            self.fields['descricao'].widget.attrs.update({'class': _TEXTAREA})
            self.fields['prazo'].widget.attrs.update({'class': _INPUT})

        self.fields['prazo'].input_formats = ['%Y-%m-%d']

        visible = get_visible_users(user) if user is not None else None
        if visible is not None:
            self.fields['responsavel'].queryset = visible.order_by('nome', 'email')
            if not is_create:
                self.fields['responsavel'].widget.attrs.update({'class': _SELECT})
            self.fields['responsavel'].label_from_instance = (
                lambda u: u.nome or u.email
            )
            if is_create and pdi is not None:
                self.fields['responsavel'].initial = pdi.usuario_id
        else:
            from apps.accounts.models import CustomUser

            self.fields['responsavel'].queryset = CustomUser.objects.none()

    def clean(self):
        cleaned = super().clean()
        if self.instance.pk:
            return cleaned

        titulo = cleaned.get('titulo_acao', '').strip()
        objetivos = cleaned.get('descricao', '').strip()

        if not titulo:
            self.add_error(
                'titulo_acao',
                'Informe o título da ação.',
            )
            return cleaned

        cleaned['descricao'] = (
            f'{titulo}\n\n{objetivos}' if objetivos else titulo
        )
        return cleaned

    def clean_prazo(self):
        prazo = self.cleaned_data['prazo']
        if self.instance.pk is None and prazo < timezone.localdate():
            raise forms.ValidationError(
                'O prazo deve ser igual ou posterior à data de hoje.',
            )
        return prazo

    def clean_responsavel(self):
        responsavel = self.cleaned_data['responsavel']
        if self.user is None or not user_in_scope(self.user, responsavel.pk):
            raise forms.ValidationError(
                'Você não tem permissão para atribuir este responsável.',
            )
        return responsavel
