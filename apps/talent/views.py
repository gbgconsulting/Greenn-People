"""Views do domínio talent (matriz 9-box, classificação e visibilidade)."""

from __future__ import annotations

import json
from collections.abc import Iterable

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import QuerySet
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
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


def _parse_optional_int(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _matrix_classificacoes_qs(
    viewer,
    ciclo: Ciclo,
    *,
    area_id: int | None = None,
    cargo_id: int | None = None,
) -> QuerySet[ClassificacaoTalento]:
    """Queryset da grade (ciclo + escopo + filtros área/cargo)."""
    qs = ClassificacaoTalento.objects.select_related(
        'usuario',
        'usuario__area',
        'usuario__cargo',
        'ciclo',
    ).filter(ciclo=ciclo)
    visible = get_visible_users(viewer).filter(is_active=True)
    qs = qs.filter(usuario__in=visible)
    if area_id is not None:
        qs = qs.filter(usuario__area_id=area_id)
    if cargo_id is not None:
        qs = qs.filter(usuario__cargo_id=cargo_id)
    return qs.order_by('usuario__nome', 'usuario__email')


def _find_cell(
    classificacoes: Iterable[ClassificacaoTalento],
    desempenho: int,
    potencial: int,
) -> dict | None:
    for row in build_matriz_rows(classificacoes):
        for cell in row['cells']:
            if cell['desempenho'] == desempenho and cell['potencial'] == potencial:
                return cell
    return None


def _hx_show_message(response: HttpResponse, message: str, *, level: str = 'success') -> HttpResponse:
    response['HX-Trigger'] = json.dumps(
        {'showMessage': {'message': message, 'level': level}},
    )
    return response


def _render_matrix_cells_oob(
    request,
    *,
    ciclo: Ciclo,
    area_id: int | None,
    cargo_id: int | None,
    coords: set[tuple[int, int]],
    cell_template: str = 'talent/partials/_cell.html',
) -> str:
    """Partial(s) de célula com ``hx-swap-oob`` para refresh pontual da grade."""
    classificacoes = list(
        _matrix_classificacoes_qs(
            request.user,
            ciclo,
            area_id=area_id,
            cargo_id=cargo_id,
        ),
    )
    parts: list[str] = []
    for desempenho, potencial in sorted(coords):
        cell = _find_cell(classificacoes, desempenho, potencial)
        if cell is None:
            continue
        parts.append(
            render_to_string(
                cell_template,
                {
                    'cell': cell,
                    'oob': True,
                    'filtro_area_id': area_id,
                    'filtro_cargo_id': cargo_id,
                    'is_admin_viewer': bool(
                        getattr(request.user, 'is_admin', False),
                    ),
                },
                request=request,
            ),
        )
    return ''.join(parts)


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
        # Única fonte de escopo: usuario__in=get_visible_users (authz-scope / T029).
        ciclo = self._resolve_ciclo()
        if ciclo is None:
            return ClassificacaoTalento.objects.none()
        return _matrix_classificacoes_qs(
            self.request.user,
            ciclo,
            area_id=_parse_optional_int(self.request.GET.get('area')),
            cargo_id=_parse_optional_int(self.request.GET.get('cargo')),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ciclo = self._resolve_ciclo()
        area_id = _parse_optional_int(self.request.GET.get('area'))
        cargo_id = _parse_optional_int(self.request.GET.get('cargo'))

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


class MatrixDrawerView(LoginRequiredMixin, RequiresManagerOrAdminMixin, View):
    """GET HTMX: drawer in-matrix (write se admin; read-only se gerente)."""

    http_method_names = ['get', 'head', 'options']
    template_name = 'talent/partials/_drawer.html'

    def get(self, request, user_pk):
        if not is_htmx(request):
            return HttpResponseRedirect(reverse('talent:matrix'))

        visible = get_visible_users(request.user).filter(is_active=True)
        colaborador = get_object_or_404(visible, pk=user_pk)

        ciclo = self._resolve_ciclo()
        if ciclo is None:
            raise Http404('Ciclo não encontrado.')

        classificacao = get_object_or_404(
            ClassificacaoTalento.objects.select_related(
                'usuario',
                'usuario__area',
                'usuario__cargo',
                'ciclo',
            ),
            usuario=colaborador,
            ciclo=ciclo,
        )

        drawer_writable = bool(getattr(request.user, 'is_admin', False))
        return render(
            request,
            self.template_name,
            {
                'classificacao': classificacao,
                'drawer_writable': drawer_writable,
                'desempenho_label': NIVEL_LABEL[classificacao.desempenho],
                'potencial_label': NIVEL_LABEL[classificacao.potencial],
                'area': request.GET.get('area') or None,
                'cargo': request.GET.get('cargo') or None,
            },
        )

    def _resolve_ciclo(self) -> Ciclo | None:
        ciclo_id = self.request.GET.get('ciclo')
        if ciclo_id:
            try:
                return Ciclo.objects.filter(pk=int(ciclo_id)).first()
            except (TypeError, ValueError):
                return get_open_ciclo()
        return get_open_ciclo()


class MatrixPotencialView(LoginRequiredMixin, RequiresAdminMixin, View):
    """POST: salvar potencial via drawer (HTMX) ou redirect legado."""

    http_method_names = ['post', 'options']
    drawer_template = 'talent/partials/_drawer.html'
    cell_template = 'talent/partials/_cell.html'

    def post(self, request, user_pk):
        ciclo = self._resolve_ciclo()
        if ciclo is None:
            raise Http404('Ciclo não encontrado.')

        colaborador = get_object_or_404(
            CustomUser.objects.select_related('area', 'cargo'),
            pk=user_pk,
        )
        classificacao = get_object_or_404(
            ClassificacaoTalento.objects.select_related(
                'usuario',
                'usuario__area',
                'usuario__cargo',
                'ciclo',
            ),
            usuario=colaborador,
            ciclo=ciclo,
        )

        area_raw = request.POST.get('area') or None
        cargo_raw = request.POST.get('cargo') or None
        area_id = _parse_optional_int(area_raw)
        cargo_id = _parse_optional_int(cargo_raw)
        drawer_ctx_base = {
            'drawer_writable': True,
            'desempenho_label': NIVEL_LABEL[classificacao.desempenho],
            'area': area_raw,
            'cargo': cargo_raw,
        }

        potencial = _parse_optional_int(request.POST.get('potencial'))
        if potencial not in (1, 2, 3):
            erro = 'Potencial deve ser um inteiro entre 1 e 3.'
            if is_htmx(request):
                return self._drawer_error_response(
                    request,
                    classificacao,
                    drawer_ctx_base,
                    erro,
                )
            messages.error(request, erro)
            return HttpResponseRedirect(
                f"{reverse('talent:matrix')}?ciclo={ciclo.pk}",
            )

        old_desempenho = classificacao.desempenho
        old_potencial = classificacao.potencial

        try:
            classificacao = upsert_classification(
                usuario=colaborador,
                ciclo=ciclo,
                potencial=potencial,
                admin=request.user,
            )
        except PermissionDenied as exc:
            msg = str(exc) or 'Você não tem permissão para salvar o potencial.'
            if is_htmx(request):
                return self._drawer_error_response(
                    request,
                    classificacao,
                    drawer_ctx_base,
                    msg,
                )
            messages.error(request, msg)
            return HttpResponseRedirect(
                f"{reverse('talent:matrix')}?ciclo={ciclo.pk}",
            )
        except ValidationError as exc:
            msg = '; '.join(exc.messages) if getattr(exc, 'messages', None) else str(exc)
            if is_htmx(request):
                return self._drawer_error_response(
                    request,
                    classificacao,
                    drawer_ctx_base,
                    msg,
                )
            messages.error(request, msg)
            return HttpResponseRedirect(
                f"{reverse('talent:matrix')}?ciclo={ciclo.pk}",
            )

        classificacao = (
            ClassificacaoTalento.objects.select_related(
                'usuario',
                'usuario__area',
                'usuario__cargo',
                'ciclo',
            ).get(pk=classificacao.pk)
        )
        success_msg = (
            f'Potencial atualizado: {NIVEL_LABEL[classificacao.potencial]} '
            f'({classificacao.get_quadrante_display()}).'
        )

        if not is_htmx(request):
            messages.success(request, success_msg)
            return HttpResponseRedirect(
                f"{reverse('talent:matrix')}?ciclo={ciclo.pk}",
            )

        drawer_html = render_to_string(
            self.drawer_template,
            {
                'classificacao': classificacao,
                'drawer_writable': True,
                'desempenho_label': NIVEL_LABEL[classificacao.desempenho],
                'area': area_raw,
                'cargo': cargo_raw,
            },
            request=request,
        )

        cells_html = self._render_cells_oob(
            request,
            ciclo=ciclo,
            area_id=area_id,
            cargo_id=cargo_id,
            coords={
                (old_desempenho, old_potencial),
                (classificacao.desempenho, classificacao.potencial),
            },
        )
        response = HttpResponse(drawer_html + cells_html)
        return _hx_show_message(response, success_msg, level='success')

    def _drawer_error_response(
        self,
        request,
        classificacao: ClassificacaoTalento,
        drawer_ctx_base: dict,
        message: str,
    ) -> HttpResponse:
        """Re-renderiza o drawer com erro PT-BR; grade permanece intacta (FR-005)."""
        html = render_to_string(
            self.drawer_template,
            {
                **drawer_ctx_base,
                'classificacao': classificacao,
                'potencial_error': message,
            },
            request=request,
        )
        response = HttpResponse(html)
        return _hx_show_message(response, message, level='error')

    def _render_cells_oob(
        self,
        request,
        *,
        ciclo: Ciclo,
        area_id: int | None,
        cargo_id: int | None,
        coords: set[tuple[int, int]],
    ) -> str:
        return _render_matrix_cells_oob(
            request,
            ciclo=ciclo,
            area_id=area_id,
            cargo_id=cargo_id,
            coords=coords,
            cell_template=self.cell_template,
        )

    def _resolve_ciclo(self) -> Ciclo | None:
        ciclo_id = self.request.POST.get('ciclo_id') or self.request.POST.get('ciclo')
        if ciclo_id:
            try:
                return Ciclo.objects.filter(pk=int(ciclo_id)).first()
            except (TypeError, ValueError):
                return None
        return get_open_ciclo()


class MatrixMoveView(LoginRequiredMixin, RequiresAdminMixin, View):
    """POST: move DnD potencial-only; desempenho da célula-alvo é ignorado (R4/T021).

    Card final via OOB em ``(desempenho_derivado, potencial_novo)``. Se o
    payload trouxer ``desempenho`` da célula sob o cursor ≠ derivado →
    ``SNAP_MSG`` no ``HX-Trigger`` (feedback PT-BR explícito).
    """

    http_method_names = ['post', 'options']
    cell_template = 'talent/partials/_cell.html'
    # research R4 / T021 — toast quando houve snap de linha.
    SNAP_MSG = (
        'Só o potencial é alterado por arraste; '
        'o desempenho continua derivado da nota do líder.'
    )

    def post(self, request, user_pk):
        ciclo = self._resolve_ciclo()
        if ciclo is None:
            raise Http404('Ciclo não encontrado.')

        colaborador = get_object_or_404(
            CustomUser.objects.select_related('area', 'cargo'),
            pk=user_pk,
        )
        classificacao = get_object_or_404(
            ClassificacaoTalento.objects.select_related(
                'usuario',
                'usuario__area',
                'usuario__cargo',
                'ciclo',
            ),
            usuario=colaborador,
            ciclo=ciclo,
        )

        area_id = _parse_optional_int(request.POST.get('area'))
        cargo_id = _parse_optional_int(request.POST.get('cargo'))
        # ``desempenho`` da célula-alvo pode vir no payload (debug/UI); NÃO muta.
        target_desempenho = _parse_optional_int(request.POST.get('desempenho'))

        potencial = _parse_optional_int(request.POST.get('potencial'))
        if potencial not in (1, 2, 3):
            return self._error_response(
                request,
                'Potencial deve ser um inteiro entre 1 e 3.',
                status=400,
            )

        old_desempenho = classificacao.desempenho
        old_potencial = classificacao.potencial

        # Noop: potencial inalterado → sem write material.
        if potencial == old_potencial:
            soft_msg = (
                f'Potencial inalterado: {NIVEL_LABEL[old_potencial]}.'
            )
            if not is_htmx(request):
                messages.info(request, soft_msg)
                return HttpResponseRedirect(
                    f"{reverse('talent:matrix')}?ciclo={ciclo.pk}",
                )
            response = HttpResponse(status=200)
            return _hx_show_message(response, soft_msg, level='success')

        try:
            classificacao = upsert_classification(
                usuario=colaborador,
                ciclo=ciclo,
                potencial=potencial,
                admin=request.user,
            )
        except PermissionDenied as exc:
            msg = str(exc) or 'Você não tem permissão para mover a classificação.'
            return self._error_response(request, msg, status=403)
        except ValidationError as exc:
            msg = (
                '; '.join(exc.messages)
                if getattr(exc, 'messages', None)
                else str(exc)
            )
            return self._error_response(request, msg, status=400)

        classificacao = (
            ClassificacaoTalento.objects.select_related(
                'usuario',
                'usuario__area',
                'usuario__cargo',
                'ciclo',
            ).get(pk=classificacao.pk)
        )

        snapped = (
            target_desempenho is not None
            and target_desempenho != classificacao.desempenho
        )
        if snapped:
            success_msg = self.SNAP_MSG
        else:
            success_msg = (
                f'Potencial atualizado: {NIVEL_LABEL[classificacao.potencial]} '
                f'({classificacao.get_quadrante_display()}).'
            )

        if not is_htmx(request):
            messages.success(request, success_msg)
            return HttpResponseRedirect(
                f"{reverse('talent:matrix')}?ciclo={ciclo.pk}",
            )

        # Card na célula (desempenho_derivado, potencial_novo) via OOB.
        cells_html = _render_matrix_cells_oob(
            request,
            ciclo=ciclo,
            area_id=area_id,
            cargo_id=cargo_id,
            coords={
                (old_desempenho, old_potencial),
                (classificacao.desempenho, classificacao.potencial),
            },
            cell_template=self.cell_template,
        )
        response = HttpResponse(cells_html)
        return _hx_show_message(response, success_msg, level='success')

    def _error_response(
        self,
        request,
        message: str,
        *,
        status: int,
    ) -> HttpResponse:
        """Erro PT-BR; HTMX → toast; não-HTMX → redirect (grade intacta)."""
        if is_htmx(request):
            response = HttpResponse(status=status)
            return _hx_show_message(response, message, level='error')
        messages.error(request, message)
        ciclo_id = (
            request.POST.get('ciclo_id')
            or request.POST.get('ciclo')
            or ''
        )
        if ciclo_id:
            return HttpResponseRedirect(
                f"{reverse('talent:matrix')}?ciclo={ciclo_id}",
            )
        return HttpResponseRedirect(reverse('talent:matrix'))

    def _resolve_ciclo(self) -> Ciclo | None:
        ciclo_id = self.request.POST.get('ciclo_id') or self.request.POST.get('ciclo')
        if ciclo_id:
            try:
                return Ciclo.objects.filter(pk=int(ciclo_id)).first()
            except (TypeError, ValueError):
                return None
        return get_open_ciclo()


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
    """Alterna ``visivel_ao_colaborador`` (admin, RF-25).

    HTMX (drawer): atualiza badge no drawer + card na célula (OOB) + toast.
    Não-HTMX: redirect legado para a matriz (compat).
    """

    model = ClassificacaoTalento
    http_method_names = ['post', 'options']
    queryset = ClassificacaoTalento.objects.select_related(
        'usuario',
        'usuario__area',
        'usuario__cargo',
        'ciclo',
    )
    drawer_template = 'talent/partials/_drawer.html'
    cell_template = 'talent/partials/_cell.html'

    def post(self, request, *args, **kwargs):
        classificacao = self.get_object()
        area_raw = request.POST.get('area') or None
        cargo_raw = request.POST.get('cargo') or None
        area_id = _parse_optional_int(area_raw)
        cargo_id = _parse_optional_int(cargo_raw)
        drawer_ctx = {
            'drawer_writable': True,
            'desempenho_label': NIVEL_LABEL[classificacao.desempenho],
            'area': area_raw,
            'cargo': cargo_raw,
        }

        try:
            classificacao = toggle_classification_visibility(
                classificacao,
                request.user,
            )
        except PermissionDenied as exc:
            msg = (
                str(exc)
                or 'Você não tem permissão para alterar a visibilidade.'
            )
            if is_htmx(request):
                # Re-renderiza drawer com estado anterior + toast erro (SC-004).
                html = render_to_string(
                    self.drawer_template,
                    {**drawer_ctx, 'classificacao': classificacao},
                    request=request,
                )
                response = HttpResponse(html)
                return _hx_show_message(response, msg, level='error')
            raise

        classificacao = (
            ClassificacaoTalento.objects.select_related(
                'usuario',
                'usuario__area',
                'usuario__cargo',
                'ciclo',
            ).get(pk=classificacao.pk)
        )

        nome = classificacao.usuario.nome or classificacao.usuario.email
        if classificacao.visivel_ao_colaborador:
            success_msg = f'Classificação de {nome} liberada para o colaborador.'
        else:
            success_msg = f'Classificação de {nome} ocultada do colaborador.'

        if not is_htmx(request):
            messages.success(request, success_msg)
            return HttpResponseRedirect(
                f"{reverse('talent:matrix')}?ciclo={classificacao.ciclo_id}",
            )

        drawer_html = render_to_string(
            self.drawer_template,
            {
                'classificacao': classificacao,
                'drawer_writable': True,
                'desempenho_label': NIVEL_LABEL[classificacao.desempenho],
                'area': area_raw,
                'cargo': cargo_raw,
            },
            request=request,
        )
        cells_html = _render_matrix_cells_oob(
            request,
            ciclo=classificacao.ciclo,
            area_id=area_id,
            cargo_id=cargo_id,
            coords={(classificacao.desempenho, classificacao.potencial)},
            cell_template=self.cell_template,
        )
        response = HttpResponse(drawer_html + cells_html)
        return _hx_show_message(response, success_msg, level='success')
