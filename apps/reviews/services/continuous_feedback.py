"""Feedback contínuo (fora do ciclo): AuthZ e criação no backend."""

from __future__ import annotations

from django.db import transaction
from django.http import Http404
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.accounts.services.scope import user_in_scope
from apps.audit.services import log_scope_denied
from apps.reviews.models import FeedbackContinuo


def continuous_feedback_create_allowed(autor, destinatario) -> bool:
    """True se ``autor`` pode enviar feedback contínuo a ``destinatario``.

    Regras (sempre no backend):
    - ambos autenticados / com pk
    - destinatário ativo
    - autor ≠ destinatário (gestor → colaborador)
    - destinatário no escopo hierárquico do autor
    """
    if not getattr(autor, 'pk', None) or not getattr(destinatario, 'pk', None):
        return False
    if not destinatario.is_active:
        return False
    if autor.pk == destinatario.pk:
        return False
    return user_in_scope(autor, destinatario.pk)


def continuous_feedback_list_allowed(viewer, destinatario) -> bool:
    """True se ``viewer`` pode listar feedbacks contínuos de ``destinatario``."""
    if not getattr(viewer, 'pk', None) or not getattr(destinatario, 'pk', None):
        return False
    if viewer.pk == destinatario.pk:
        return True
    return user_in_scope(viewer, destinatario.pk)


def can_acknowledge_continuous_feedback(user, feedback: FeedbackContinuo) -> bool:
    """Ciência apenas do destinatário, enquanto ``ciente_em`` estiver vazio."""
    if feedback.ciente_em is not None:
        return False
    return feedback.destinatario_id == getattr(user, 'pk', None)


def get_destinatario_in_scope_for_list(request, user_id: int) -> CustomUser:
    """Resolve destinatário para listagem; fora do escopo → Http404 + auditoria."""
    try:
        destinatario = CustomUser.objects.get(pk=user_id)
    except CustomUser.DoesNotExist as exc:
        raise Http404() from exc

    if not continuous_feedback_list_allowed(request.user, destinatario):
        log_scope_denied(request.user, destinatario)
        raise Http404()
    return destinatario


def get_destinatario_for_create(request, user_id: int) -> CustomUser:
    """Resolve destinatário para criação; fora do escopo → Http404 + auditoria."""
    try:
        destinatario = CustomUser.objects.get(pk=user_id)
    except CustomUser.DoesNotExist as exc:
        raise Http404() from exc

    if not continuous_feedback_create_allowed(request.user, destinatario):
        log_scope_denied(request.user, destinatario)
        raise Http404()
    return destinatario


def create_continuous_feedback(
    *,
    autor,
    destinatario,
    conteudo: str,
) -> FeedbackContinuo:
    """Cria feedback contínuo e agenda notificação (falha de e-mail não desfaz)."""
    if not continuous_feedback_create_allowed(autor, destinatario):
        raise PermissionError('Escopo insuficiente para enviar feedback contínuo.')

    texto = (conteudo or '').strip()
    if not texto:
        raise ValueError('Informe o conteúdo do feedback.')

    feedback = FeedbackContinuo.objects.create(
        autor=autor,
        destinatario=destinatario,
        conteudo=texto,
    )

    feedback_id = feedback.pk

    def _enqueue_notification() -> None:
        from apps.notifications.tasks import enviar_notificacao_feedback_continuo

        enviar_notificacao_feedback_continuo.delay(feedback_id)

    transaction.on_commit(_enqueue_notification)
    return feedback


def acknowledge_continuous_feedback(
    *,
    user,
    feedback: FeedbackContinuo,
) -> FeedbackContinuo:
    """Registra ciência; não altera avaliação/ciclo."""
    if not can_acknowledge_continuous_feedback(user, feedback):
        raise PermissionError('Ciência não permitida para este feedback.')

    feedback.ciente_em = timezone.now()
    feedback.save(update_fields=['ciente_em', 'updated_at'])
    return feedback
