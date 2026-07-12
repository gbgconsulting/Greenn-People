from __future__ import annotations

from django import forms

from apps.cycles.models import Ciclo
from apps.goals.models import Meta, ObjetivoEstrategico
from apps.reviews.models import Avaliacao

_INPUT = (
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent'
)
_TEXTAREA = (
    'w-full rounded-lg border border-slate-200 px-3 py-2 text-sm '
    'focus:outline-none focus:ring-2 focus:ring-emerald-500 '
    'focus:border-transparent min-h-[6rem]'
)


def get_open_ciclo() -> Ciclo | None:
    return (
        Ciclo.objects.filter(status=Ciclo.Status.ABERTO)
        .order_by('-data_inicio')
        .first()
    )


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


class MetaForm(forms.ModelForm):
    """Cadastro/edição de meta do colaborador (bloqueio fora da etapa permitida)."""

    class Meta:
        model = Meta
        fields = ('objetivo_estrategico', 'descricao')
        labels = {
            'objetivo_estrategico': 'Objetivo estratégico',
            'descricao': 'Descrição da meta',
        }
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields['objetivo_estrategico'].widget.attrs.update({'class': _INPUT})
        self.fields['descricao'].widget.attrs.update({'class': _TEXTAREA})

        ciclo = get_open_ciclo()
        objetivos = ObjetivoEstrategico.objects.none()
        if ciclo is not None:
            objetivos = ObjetivoEstrategico.objects.filter(ciclo=ciclo).order_by('id')
        self.fields['objetivo_estrategico'].queryset = objetivos
        self.fields['objetivo_estrategico'].empty_label = '— Selecione —'

    def clean(self):
        cleaned = super().clean()
        meta = self.instance if self.instance.pk else None
        owner = meta.usuario if meta is not None else self.user
        avaliacao = get_avaliacao_for_user(owner)

        if not meta_content_editable(avaliacao, meta):
            raise forms.ValidationError(
                'Não é possível criar ou editar metas fora da etapa permitida '
                '(input de metas, ou ajuste de meta pendente/reprovada).',
            )

        objetivo = cleaned.get('objetivo_estrategico')
        ciclo = get_open_ciclo()
        if objetivo is not None and ciclo is not None and objetivo.ciclo_id != ciclo.pk:
            self.add_error(
                'objetivo_estrategico',
                'Selecione um objetivo do ciclo aberto.',
            )

        return cleaned
