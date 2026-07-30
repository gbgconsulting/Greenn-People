"""US4 / T024: context processor de ciclo aberto na topbar."""

from __future__ import annotations

import pytest
from django.contrib.auth.models import AnonymousUser

from apps.core.context_processors import ciclo_aberto as ciclo_aberto_processor
from apps.cycles.models import Ciclo
from apps.cycles.services.cycle import close_cycle


@pytest.mark.django_db
def test_processor_retorna_ciclo_quando_aberto(ciclo_aberto, colaborador, rf):
    """Com status=ABERTO, o processor expõe o ciclo no contexto."""
    request = rf.get('/')
    request.user = colaborador

    ctx = ciclo_aberto_processor(request)

    assert ctx.get('ciclo_aberto') is not None
    assert ctx['ciclo_aberto'].pk == ciclo_aberto.pk
    assert ctx['ciclo_aberto'].status == Ciclo.Status.ABERTO


@pytest.mark.django_db
def test_processor_retorna_none_sem_ciclo_aberto(colaborador, rf):
    """Sem ciclo aberto, o processor expõe None (fallback na topbar)."""
    for aberto in Ciclo.objects.filter(status=Ciclo.Status.ABERTO):
        close_cycle(aberto)

    request = rf.get('/')
    request.user = colaborador

    ctx = ciclo_aberto_processor(request)

    assert ctx.get('ciclo_aberto') is None


@pytest.mark.django_db
def test_processor_anonimo_sem_bloco_de_ciclo(rf):
    """Request anônimo não recebe ciclo no contexto (topbar auth)."""
    request = rf.get('/')
    request.user = AnonymousUser()

    ctx = ciclo_aberto_processor(request)

    assert ctx.get('ciclo_aberto') is None
