from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import DetailView

from apps.audit.services import log_scope_denied
from apps.reviews.forms import SelfAssessmentFormSet, self_assessment_editable
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia


class SelfAssessmentView(LoginRequiredMixin, DetailView):
    """Autoavaliação do colaborador (etapa ``avaliacao``; escopo Self)."""

    model = Avaliacao
    template_name = 'reviews/self_assessment.html'
    context_object_name = 'avaliacao'
    http_method_names = ['get', 'post', 'head', 'options']

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.usuario_id != self.request.user.pk:
            log_scope_denied(self.request.user, obj)
            raise Http404()
        return obj

    def get_queryset(self):
        return Avaliacao.objects.select_related('ciclo', 'usuario')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        self.object = self.get_object()
        if not self_assessment_editable(self.object):
            messages.error(
                request,
                'A autoavaliação só está disponível na etapa de avaliação '
                'de um ciclo aberto.',
            )
            return HttpResponseRedirect(reverse('dashboard:personal'))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        formset = SelfAssessmentFormSet(
            request.POST,
            queryset=self._linhas_queryset(),
        )
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Autoavaliação salva com sucesso.')
            return HttpResponseRedirect(
                reverse('reviews:self_assessment', kwargs={'pk': self.object.pk}),
            )

        context = self.get_context_data(object=self.object, formset=formset)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        formset = kwargs.get('formset')
        if formset is None:
            formset = SelfAssessmentFormSet(queryset=self._linhas_queryset())

        context.update(
            {
                'formset': formset,
                'pode_editar': True,
                'linhas_vazias': len(formset.forms) == 0,
            },
        )
        return context

    def _linhas_queryset(self):
        return (
            AvaliacaoCompetencia.objects.filter(avaliacao_id=self.object.pk)
            .select_related(
                'avaliacao',
                'avaliacao__ciclo',
                'competencia',
                'competencia__escala',
            )
            .order_by('competencia__nome')
        )
