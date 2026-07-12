from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView

from apps.core.mixins import ScopedObjectMixin
from apps.pdi.forms import PDIForm
from apps.pdi.models import AcaoPDI, PDI
from apps.pdi.services.progress import calculate_pdi_progress


class PDIListView(LoginRequiredMixin, ScopedObjectMixin, ListView):
    """Listagem de PDIs no escopo hierárquico do usuário."""

    model = PDI
    template_name = 'pdi/pdi_list.html'
    context_object_name = 'pdis'
    paginate_by = 20
    scope_user_field = 'usuario'

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related('usuario', 'usuario__area', 'usuario__cargo')
            .order_by('usuario__nome', 'usuario__email', '-created_at', 'id')
        )
        status = self.request.GET.get('status', '').strip()
        if status in {c.value for c in PDI.Status}:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = []
        for pdi in context['pdis']:
            rows.append(
                {
                    'pdi': pdi,
                    'progresso': calculate_pdi_progress(pdi),
                    'is_self': pdi.usuario_id == self.request.user.pk,
                },
            )
        context.update(
            {
                'pdi_rows': rows,
                'status_filtro': self.request.GET.get('status', '').strip(),
                'status_choices': PDI.Status.choices,
                'pode_criar': True,
            },
        )
        return context


class PDICreateView(LoginRequiredMixin, ScopedObjectMixin, CreateView):
    """Cadastro de PDI para o próprio usuário ou colaborador no escopo."""

    model = PDI
    form_class = PDIForm
    template_name = 'pdi/pdi_form.html'
    scope_user_field = 'usuario'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['mostrar_usuario'] = bool(
            getattr(user, 'is_leader', False)
            or getattr(user, 'is_manager', False)
            or getattr(user, 'is_admin', False),
        )
        return context

    def form_valid(self, form):
        messages.success(self.request, 'PDI criado com sucesso.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('pdi:detail', kwargs={'pk': self.object.pk})


class PDIDetailView(LoginRequiredMixin, ScopedObjectMixin, DetailView):
    """Detalhe do PDI no escopo; IDOR → Http404 + ``log_scope_denied``."""

    model = PDI
    template_name = 'pdi/pdi_detail.html'
    context_object_name = 'pdi'
    scope_user_field = 'usuario'
    queryset = PDI.objects.select_related(
        'usuario',
        'usuario__area',
        'usuario__cargo',
        'usuario__line_manager',
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pdi = self.object
        acoes = (
            AcaoPDI.objects.filter(pdi_id=pdi.pk)
            .select_related('responsavel')
            .order_by('prazo', 'id')
        )
        context.update(
            {
                'colaborador': pdi.usuario,
                'is_self': pdi.usuario_id == self.request.user.pk,
                'progresso': calculate_pdi_progress(pdi),
                'acoes': acoes,
            },
        )
        return context
