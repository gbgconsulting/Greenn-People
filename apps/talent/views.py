"""Views do domínio talent (matriz 9-box)."""

from __future__ import annotations

from collections import defaultdict

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import QuerySet
from django.views.generic import ListView

from apps.accounts.services.scope import get_visible_users
from apps.core.mixins import RequiresManagerOrAdminMixin
from apps.cycles.models import Ciclo
from apps.goals.forms import get_open_ciclo
from apps.organization.models import Area, Cargo
from apps.talent.models import ClassificacaoTalento

# Ordem visual da matriz: desempenho alto no topo, potencial crescente à direita.
_DESEMPENHO_ROWS = (3, 2, 1)
_POTENCIAL_COLS = (1, 2, 3)
_NIVEL_LABEL = {1: 'Baixo', 2: 'Médio', 3: 'Alto'}
_QUADRANTE_MEMBER = {
    (3, 1): 'ALTO_BAIXO',
    (3, 2): 'ALTO_MEDIO',
    (3, 3): 'ALTO_ALTO',
    (2, 1): 'MEDIO_BAIXO',
    (2, 2): 'MEDIO_MEDIO',
    (2, 3): 'MEDIO_ALTO',
    (1, 1): 'BAIXO_BAIXO',
    (1, 2): 'BAIXO_MEDIO',
    (1, 3): 'BAIXO_ALTO',
}


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

        by_quadrante: dict[str, list[ClassificacaoTalento]] = defaultdict(list)
        for item in context['object_list']:
            by_quadrante[item.quadrante].append(item)

        rows = []
        for desempenho in _DESEMPENHO_ROWS:
            cells = []
            for potencial in _POTENCIAL_COLS:
                member_name = _QUADRANTE_MEMBER[(desempenho, potencial)]
                quadrante = ClassificacaoTalento.Quadrante[member_name]
                cells.append(
                    {
                        'desempenho': desempenho,
                        'potencial': potencial,
                        'quadrante': quadrante.value,
                        'label': quadrante.label,
                        'itens': by_quadrante.get(quadrante.value, []),
                    },
                )
            rows.append(
                {
                    'desempenho': desempenho,
                    'desempenho_label': _NIVEL_LABEL[desempenho],
                    'cells': cells,
                },
            )

        context['ciclo_filtro'] = ciclo
        context['ciclo_aberto'] = get_open_ciclo()
        context['ciclos'] = Ciclo.objects.order_by('-data_inicio', 'nome')
        context['areas'] = Area.objects.filter(is_active=True).order_by('nome')
        context['cargos'] = Cargo.objects.filter(is_active=True).order_by('nivel', 'nome')
        context['filtro_area_id'] = area_id
        context['filtro_cargo_id'] = cargo_id
        context['matriz_rows'] = rows
        context['potencial_labels'] = [_NIVEL_LABEL[p] for p in _POTENCIAL_COLS]
        context['total_classificados'] = len(context['object_list'])
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
