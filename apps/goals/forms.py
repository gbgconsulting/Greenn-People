from __future__ import annotations

from decimal import Decimal

from django import forms

from apps.cycles.models import Ciclo
from apps.goals.models import Meta, ObjetivoEstrategico
from apps.reviews.models import Avaliacao

_INPUT = (
    'w-full rounded-lg border border-transparent bg-slate-100 px-4 py-3 '
    'font-ui text-sm text-slate-800 transition-all '
    'placeholder:text-slate-400 hover:bg-slate-200/60 '
    'focus:border-emerald-600 focus:bg-white focus:outline-none '
    'focus:ring-1 focus:ring-emerald-600'
)
_TEXTAREA = (
    'w-full min-h-[7.5rem] resize-y rounded-lg border border-transparent '
    'bg-slate-100 px-4 py-3 font-ui text-sm text-slate-800 transition-all '
    'placeholder:text-slate-400 hover:bg-slate-200/60 '
    'focus:border-emerald-600 focus:bg-white focus:outline-none '
    'focus:ring-1 focus:ring-emerald-600'
)


def get_open_ciclos():
    """QuerySet canônico de ciclos ``aberto``, mais recente primeiro.

    Ordenação: ``-data_inicio``, ``nome``. Com multi-open pode haver N.
    """
    return Ciclo.objects.filter(status=Ciclo.Status.ABERTO).order_by(
        '-data_inicio',
        'nome',
    )


def get_open_ciclo() -> Ciclo | None:
    """Default operacional: primeiro de ``get_open_ciclos()`` (ou ``None``).

    Não significa “único aberto” — use ``get_open_ciclos()`` quando a lista
    completa for necessária (seletor, topbar, governança).
    """
    return get_open_ciclos().first()


def get_avaliacao_for_user(user, ciclo: Ciclo | None = None) -> Avaliacao | None:
    ciclo = ciclo or get_open_ciclo()
    if ciclo is None or not getattr(user, 'pk', None):
        return None
    return Avaliacao.objects.filter(ciclo=ciclo, usuario=user).first()


def meta_content_editable(avaliacao: Avaliacao | None, meta: Meta | None = None) -> bool:
    """True se descrição/objetivo podem ser criados ou editados na etapa atual."""
    if avaliacao is None or avaliacao.ciclo.status != Ciclo.Status.ABERTO:
        return False

    etapa = avaliacao.etapa
    if etapa == Avaliacao.Etapa.INPUT_METAS:
        return True

    if etapa == Avaliacao.Etapa.APROVACAO_METAS and meta is not None:
        return meta.status in (
            Meta.Status.PENDENTE,
            Meta.Status.REPROVADA,
        )

    return False


def meta_progress_editable(
    avaliacao: Avaliacao | None,
    meta: Meta | None = None,
) -> bool:
    """True se progresso pode ser registrado na etapa atual."""
    if avaliacao is None or avaliacao.ciclo.status != Ciclo.Status.ABERTO:
        return False

    etapa = avaliacao.etapa
    if etapa == Avaliacao.Etapa.RESULTADOS:
        if meta is not None and meta.status != Meta.Status.APROVADA:
            return False
        return True

    if etapa == Avaliacao.Etapa.APROVACAO_RESULTADOS and meta is not None:
        return (
            meta.status == Meta.Status.APROVADA
            and meta.status_resultado == Meta.StatusResultado.REPROVADO
        )

    return False


def is_meta_approver(approver, meta: Meta) -> bool:
    """True se ``approver`` é o aprovador válido da meta (admin ou line_manager).

    Espelha ``approval._ensure_approver`` / FR-014: admin sempre; líder comum
    só se for o ``line_manager`` do colaborador (sem surface de bypass).
    """
    if getattr(approver, 'is_admin', False):
        return True
    manager_id = meta.usuario.line_manager_id
    if manager_id is None:
        return False
    return getattr(approver, 'pk', None) == manager_id


def meta_approval_actionable(
    avaliacao: Avaliacao | None,
    meta: Meta | None,
    approver,
) -> bool:
    """True se o aprovador pode aprovar/reprovar a meta na etapa atual."""
    if (
        avaliacao is None
        or meta is None
        or avaliacao.ciclo.status != Ciclo.Status.ABERTO
        or not is_meta_approver(approver, meta)
    ):
        return False

    if avaliacao.etapa == Avaliacao.Etapa.APROVACAO_METAS:
        return meta.status == Meta.Status.PENDENTE

    if avaliacao.etapa == Avaliacao.Etapa.APROVACAO_RESULTADOS:
        return (
            meta.status == Meta.Status.APROVADA
            and meta.status_resultado == Meta.StatusResultado.PENDENTE
        )

    return False


class ObjetivoEstrategicoForm(forms.ModelForm):
    """Cadastro/edição de objetivo estratégico vinculado a um ciclo (admin RH)."""

    class Meta:
        model = ObjetivoEstrategico
        fields = ('descricao',)
        labels = {
            'descricao': 'Descrição',
        }
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descricao'].widget.attrs.update({'class': _TEXTAREA})


class MetaForm(forms.ModelForm):
    """Cadastro/edição de meta do colaborador (bloqueio fora da etapa permitida)."""

    class Meta:
        model = Meta
        fields = ('objetivo_estrategico', 'descricao')
        labels = {
            'objetivo_estrategico': 'Objetivo Estratégico Relacionado',
            'descricao': 'Título da Meta',
        }
        widgets = {
            'descricao': forms.TextInput(),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['objetivo_estrategico'].widget.attrs.update({'class': _INPUT})
        self.fields['descricao'].widget.attrs.update(
            {
                'class': _INPUT,
                'placeholder': (
                    'Ex: Reduzir tempo de resposta do suporte em 20%'
                ),
            },
        )

        ciclo = get_open_ciclo()
        objetivos = ObjetivoEstrategico.objects.none()
        if ciclo is not None:
            objetivos = ObjetivoEstrategico.objects.filter(ciclo=ciclo).order_by('id')
        self.fields['objetivo_estrategico'].queryset = objetivos
        self.fields['objetivo_estrategico'].empty_label = (
            'Selecione um objetivo ativo do ciclo...'
        )

    def clean(self):
        cleaned = super().clean()
        meta = self.instance if self.instance.pk else None
        owner = meta.usuario if meta is not None else self.user
        avaliacao = get_avaliacao_for_user(owner)

        if not meta_content_editable(avaliacao, meta):
            raise forms.ValidationError(
                'Não é possível criar ou editar metas fora da etapa permitida '
                '(etapa de metas, ou ajuste de meta pendente/reprovada).',
            )

        objetivo = cleaned.get('objetivo_estrategico')
        ciclo = get_open_ciclo()
        if objetivo is not None and ciclo is not None and objetivo.ciclo_id != ciclo.pk:
            self.add_error(
                'objetivo_estrategico',
                'Selecione um objetivo do ciclo aberto.',
            )

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if instance.pk and instance.status == Meta.Status.REPROVADA:
            avaliacao = get_avaliacao_for_user(instance.usuario)
            if (
                avaliacao is not None
                and avaliacao.etapa == Avaliacao.Etapa.APROVACAO_METAS
            ):
                instance.reopen()
        if commit:
            instance.save()
        return instance


class MetaProgressForm(forms.ModelForm):
    """Atualização de progresso binário (0 / 50 / 100) na etapa resultados."""

    progresso = forms.TypedChoiceField(
        choices=(
            ('0', 'Não iniciada (0%)'),
            ('50', 'Em andamento (50%)'),
            ('100', 'Concluída (100%)'),
        ),
        coerce=lambda value: Decimal(str(value)),
        label='Progresso',
        error_messages={
            'required': 'Selecione o estado do progresso.',
            'invalid_choice': (
                'Selecione um dos estados: Não iniciada (0%), '
                'Em andamento (50%) ou Concluída (100%).'
            ),
        },
    )

    class Meta:
        model = Meta
        fields = ('progresso',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['progresso'].required = True
        self.fields['progresso'].widget = forms.RadioSelect(
            attrs={'class': 'sr-only peer'},
        )
        # Valor inicial só pré-seleciona se já for um marco binário canônico.
        instance = getattr(self, 'instance', None)
        if instance is not None and instance.pk and not self.is_bound:
            normalizado = instance.progresso_binario_normalizado()
            if normalizado is not None:
                self.initial['progresso'] = str(int(normalizado))
            else:
                self.initial.pop('progresso', None)

    def clean_progresso(self):
        progresso = self.cleaned_data['progresso']
        if progresso not in Meta.PROGRESSO_BINARIO_VALORES:
            raise forms.ValidationError(
                'Selecione um dos estados: Não iniciada (0%), '
                'Em andamento (50%) ou Concluída (100%).',
            )
        return progresso

    def clean(self):
        cleaned = super().clean()
        meta = self.instance if self.instance.pk else None
        owner = meta.usuario if meta is not None else None
        avaliacao = get_avaliacao_for_user(owner) if owner is not None else None

        if not meta_progress_editable(avaliacao, meta):
            raise forms.ValidationError(
                'O progresso só pode ser atualizado na etapa de resultados '
                'para metas aprovadas, ou após reprovação de um resultado '
                'em ciclo aberto.',
            )

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        if (
            instance.pk
            and instance.status_resultado == Meta.StatusResultado.REPROVADO
        ):
            avaliacao = get_avaliacao_for_user(instance.usuario)
            if (
                avaliacao is not None
                and avaliacao.etapa == Avaliacao.Etapa.APROVACAO_RESULTADOS
            ):
                instance.reopen_resultado()
        if commit:
            instance.save()
        return instance
