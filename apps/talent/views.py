"""Views do domínio talent (matriz 9-box, classificação e visibilidade)."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import QuerySet
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import FormView, ListView, TemplateView
from django.views.generic.detail import SingleObjectMixin

from apps.accounts.models import CustomUser
from apps.accounts.services.scope import get_visible_users
from apps.core.htmx import is_htmx
from apps.core.mixins import RequiresAdminMixin, RequiresManagerOrAdminMixin
from apps.cycles.models import Ciclo
from apps.goals.forms import get_open_ciclo
from apps.organization.models import Area, Cargo
from apps.reviews.models import Avaliacao
from apps.talent.forms import ClassificacaoForm
from apps.talent.models import ClassificacaoTalento
from apps.talent.services.classification import (
    derive_desempenho,
    get_visible_classification_for_collaborator,
    toggle_classification_visibility,
    upsert_classification,
)
from apps.talent.services.matrix_layout import (
    NIVEL_LABEL,
    build_matriz_rows,
    potencial_labels,
)


class MyClassificationView(LoginRequiredMixin, TemplateView):
    """Classificação 9-box do próprio colaborador (RF-25 / ``visivel_ao_colaborador``)."""

    template_name = 'talent/my_classification.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ciclo = self._resolve_ciclo()
        classificacao = get_visible_classification_for_collaborator(
            self.request.user,
            ciclo=ciclo,
        )
        # Registro existe mas ainda oculto: não vazar desempenho/potencial/quadrante.
        oculto = False
        if classificacao is None and ciclo is not None:
            oculto = ClassificacaoTalento.objects.filter(
                usuario=self.request.user,
                ciclo=ciclo,
                visivel_ao_colaborador=False,
            ).exists()

        context['ciclo_filtro'] = ciclo
        context['ciclo_aberto'] = get_open_ciclo()
        context['ciclos'] = Ciclo.objects.order_by('-data_inicio', 'nome')
        context['classificacao'] = classificacao
        context['classificacao_oculta'] = oculto
        context['desempenho_label'] = (
            NIVEL_LABEL[classificacao.desempenho] if classificacao else None
        )
        context['potencial_label'] = (
            NIVEL_LABEL[classificacao.potencial] if classificacao else None
        )
        return context

    def _resolve_ciclo(self) -> Ciclo | None:
        ciclo_id = self.request.GET.get('ciclo')
        if ciclo_id:
            try:
                return Ciclo.objects.filter(pk=int(ciclo_id)).first()
            except (TypeError, ValueError):
                return get_open_ciclo()
        return get_open_ciclo()


class TalentMatrixView(LoginRequiredMixin, RequiresManagerOrAdminMixin, ListView):
    """Matriz 9-box com filtros área/cargo e escopo hierárquico (US5 / FR-011)."""

    model = ClassificacaoTalento
    template_name = 'talent/matrix.html'
    context_object_name = 'classificacoes'
    paginate_by = None  # grade completa; filtros reduzem o conjunto

    def get_queryset(self) -> QuerySet[ClassificacaoTalento]:
        qs = ClassificacaoTalento.objects.select_related(
            'usuario',
            'usuario__area',
            'usuario__cargo',
            'ciclo',
        ).order_by('usuario__nome', 'usuario__email')

        ciclo = self._resolve_ciclo()
        if ciclo is None:
            return qs.none()
        qs = qs.filter(ciclo=ciclo)

        visible = get_visible_users(self.request.user).filter(is_active=True)
        qs = qs.filter(usuario__in=visible)

        area_id = self._parse_optional_int('area')
        if area_id is not None:
            qs = qs.filter(usuario__area_id=area_id)

        cargo_id = self._parse_optional_int('cargo')
        if cargo_id is not None:
            qs = qs.filter(usuario__cargo_id=cargo_id)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ciclo = self._resolve_ciclo()
        area_id = self._parse_optional_int('area')
        cargo_id = self._parse_optional_int('cargo')

        context['ciclo_filtro'] = ciclo
        context['ciclo_aberto'] = get_open_ciclo()
        context['ciclos'] = Ciclo.objects.order_by('-data_inicio', 'nome')
        context['areas'] = Area.objects.filter(is_active=True).order_by('nome')
        context['cargos'] = Cargo.objects.filter(is_active=True).order_by('nivel', 'nome')
        context['filtro_area_id'] = area_id
        context['filtro_cargo_id'] = cargo_id
        context['matriz_rows'] = build_matriz_rows(context['object_list'])
        context['potencial_labels'] = potencial_labels()
        context['total_classificados'] = len(context['object_list'])
        context['is_admin_viewer'] = bool(
            getattr(self.request.user, 'is_admin', False),
        )
        return context

    def _resolve_ciclo(self) -> Ciclo | None:
        ciclo_id = self.request.GET.get('ciclo')
        if ciclo_id:
            try:
                return Ciclo.objects.filter(pk=int(ciclo_id)).first()
            except (TypeError, ValueError):
                return get_open_ciclo()
        return get_open_ciclo()

    def _parse_optional_int(self, key: str) -> int | None:
        raw = self.request.GET.get(key)
        if not raw:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None


class MatrixDrawerView(LoginRequiredMixin, RequiresManagerOrAdminMixin, View):
    """Stub HTMX: abre drawer in-matrix (implementação completa em US1 / T013)."""

    http_method_names = ['get', 'head', 'options']

    def get(self, request, user_pk):
        if not is_htmx(request):
            return HttpResponseRedirect(reverse('talent:matrix'))
        # Placeholder até T012/T013 preencherem ``_drawer.html``.
        return HttpResponse(
            (
                f'<aside class="p-4 text-sm text-slate-500" data-user-pk="{user_pk}">'
                'Drawer em construção.</aside>'
            ),
            content_type='text/html; charset=utf-8',
        )


class MatrixPotencialView(LoginRequiredMixin, RequiresAdminMixin, View):
    """Stub HTMX: salvar potencial via drawer (implementação em US1 / T015)."""

    http_method_names = ['post', 'options']

    def post(self, request, user_pk):
        # Endpoint reservado; lógica em T015.
        return HttpResponse(status=405)


class MatrixMoveView(LoginRequiredMixin, RequiresAdminMixin, View):
    """Stub HTMX: persistir move DnD potencial-only (implementação em US2)."""

    http_method_names = ['post', 'options']

    def post(self, request, user_pk):
        # Endpoint reservado; lógica em US2.
        return HttpResponse(status=405)


class ClassifyTalentView(LoginRequiredMixin, RequiresAdminMixin, FormView):
    """Admin define potencial manual e persiste classificação 9-box (RF-24)."""

    form_class = ClassificacaoForm
    template_name = 'talent/classify.html'
    success_url = reverse_lazy('talent:matrix')

    def dispatch(self, request, *args, **kwargs):
        self.colaborador = get_object_or_404(
            CustomUser.objects.select_related('area', 'cargo'),
            pk=kwargs['user_pk'],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        ciclo = get_open_ciclo()
        if ciclo is not None:
            initial['ciclo'] = ciclo
            existing = ClassificacaoTalento.objects.filter(
                usuario=self.colaborador,
                ciclo=ciclo,
            ).first()
            if existing is not None:
                initial['potencial'] = existing.potencial
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['colaborador'] = self.colaborador
        form = context.get('form')
        ciclo = None
        if form is not None:
            if form.is_bound:
                raw_ciclo = form.data.get('ciclo')
                if raw_ciclo:
                    try:
                        ciclo = Ciclo.objects.filter(pk=int(raw_ciclo)).first()
                    except (TypeError, ValueError):
                        ciclo = None
            else:
                ciclo = form.initial.get('ciclo') or get_open_ciclo()
                if isinstance(ciclo, int):
                    ciclo = Ciclo.objects.filter(pk=ciclo).first()
        context['ciclo_preview'] = ciclo
        context['desempenho_preview'] = self._preview_desempenho(ciclo)
        context['classificacao_atual'] = None
        if ciclo is not None:
            context['classificacao_atual'] = ClassificacaoTalento.objects.filter(
                usuario=self.colaborador,
                ciclo=ciclo,
            ).first()
        return context

    def form_valid(self, form):
        ciclo = form.cleaned_data['ciclo']
        potencial = form.cleaned_data['potencial']
        try:
            classificacao = upsert_classification(
                usuario=self.colaborador,
                ciclo=ciclo,
                potencial=potencial,
                admin=self.request.user,
            )
        except PermissionDenied as exc:
            messages.error(self.request, str(exc))
            return self.form_invalid(form)
        except ValidationError as exc:
            for message in exc.messages:
                form.add_error(None, message)
            return self.form_invalid(form)

        messages.success(
            self.request,
            (
                f'Classificação salva: desempenho {NIVEL_LABEL[classificacao.desempenho]}, '
                f'potencial {NIVEL_LABEL[classificacao.potencial]} '
                f'({classificacao.get_quadrante_display()}).'
            ),
        )
        return HttpResponseRedirect(
            f"{reverse('talent:matrix')}?ciclo={ciclo.pk}",
        )

    def _preview_desempenho(self, ciclo: Ciclo | None) -> dict | None:
        if ciclo is None:
            return None
        avaliacao = Avaliacao.objects.filter(
            usuario=self.colaborador,
            ciclo=ciclo,
        ).first()
        if avaliacao is None or avaliacao.nota_final_lider is None:
            return {
                'disponivel': False,
                'mensagem': 'Sem nota_final_lider neste ciclo; não é possível derivar desempenho.',
            }
        nivel = derive_desempenho(avaliacao.nota_final_lider)
        return {
            'disponivel': True,
            'nivel': nivel,
            'label': NIVEL_LABEL[nivel],
            'nota_final_lider': avaliacao.nota_final_lider,
        }


class ToggleVisibilityView(
    LoginRequiredMixin,
    RequiresAdminMixin,
    SingleObjectMixin,
    View,
):
    """Alterna ``visivel_ao_colaborador`` (admin, RF-25)."""

    model = ClassificacaoTalento
    http_method_names = ['post', 'options']
    queryset = ClassificacaoTalento.objects.select_related('usuario', 'ciclo')

    def post(self, request, *args, **kwargs):
        classificacao = self.get_object()
        classificacao = toggle_classification_visibility(classificacao, request.user)

        nome = classificacao.usuario.nome or classificacao.usuario.email
        if classificacao.visivel_ao_colaborador:
            messages.success(
                request,
                f'Classificação de {nome} liberada para o colaborador.',
            )
        else:
            messages.success(
                request,
                f'Classificação de {nome} ocultada do colaborador.',
            )

        return HttpResponseRedirect(
            f"{reverse('talent:matrix')}?ciclo={classificacao.ciclo_id}",
        )
