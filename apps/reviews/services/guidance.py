"""Orientação de próximo passo (guidance UX) — módulo puro de leitura.

Feature ``008-cycle-guidance-ux``. Deriva DTOs de apresentação a partir do estado
já existente (etapa, ciclo, papel). Não persiste regra nem altera fluxo.

**FR-013 / denylist**: este módulo MUST NÃO alterar nem importar mutators de
máquina de estados (``advance_stage`` / ``can_advance``), aprovação/reprovação
(``approve_*`` / ``reject_*``), fórmulas (``calcular_*``), AuthZ/escopo, models,
migrations ou URLs de domínio. Somente leitura para context/templates.

Teste de ouro: desligar este módulo / CSS de guidance não muda resultado de
negócio (avanço, aprovação, nota, AuthZ, abertura de ciclo).

**Zero write** (checklist de ``contracts/guidance-derivation.md``) — este módulo
e seus consumidores de apresentação MUST cumprir:

- ``guidance.py`` sem ``.save()`` em entidades de ciclo/avaliação/meta/feedback
- Sem chamar ``advance_stage`` / ``approve_*`` / ``calcular_nota_*``
- Sem ``transaction.atomic`` de domínio neste módulo
- Views só passam DTO no context (sem side effects de escrita via guidance)
- Testes de stage/scope continuam PASS sem alterar asserts de negócio
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

# Valores canônicos de ``Avaliacao.Etapa`` (sem importar models — zero side effect).
ETAPA_INPUT_METAS = 'input_metas'
ETAPA_APROVACAO_METAS = 'aprovacao_metas'
ETAPA_RESULTADOS = 'resultados'
ETAPA_APROVACAO_RESULTADOS = 'aprovacao_resultados'
ETAPA_AVALIACAO = 'avaliacao'
ETAPA_FEEDBACK = 'feedback'

# Ordem canônica das 6 etapas (espelha ``Avaliacao.Etapa``).
STAGE_ORDER: tuple[str, ...] = (
    ETAPA_INPUT_METAS,
    ETAPA_APROVACAO_METAS,
    ETAPA_RESULTADOS,
    ETAPA_APROVACAO_RESULTADOS,
    ETAPA_AVALIACAO,
    ETAPA_FEEDBACK,
)

STAGE_LABELS: Mapping[str, str] = {
    ETAPA_INPUT_METAS: 'Input de metas',
    ETAPA_APROVACAO_METAS: 'Aprovação de metas',
    ETAPA_RESULTADOS: 'Resultados',
    ETAPA_APROVACAO_RESULTADOS: 'Aprovação de resultados',
    ETAPA_AVALIACAO: 'Avaliação',
    ETAPA_FEEDBACK: 'Feedback',
}

GuidanceRole = Literal['colaborador', 'lider', 'rh']
StageVisualState = Literal['concluida', 'atual', 'futura', 'bloqueada']

ALLOWED_CTA_URL_NAMES: frozenset[str] = frozenset(
    {
        'dashboard:personal',
        'dashboard:team',
        'goals:meta_list',
        'reviews:self_assessment',
        'reviews:leader_assessment',
        'reviews:feedback_create',
        'reviews:feedback_list',
        'reviews:feedback_acknowledge',
        'reviews:detail',
    }
)


@dataclass(frozen=True)
class NextStepGuidance:
    """DTO de apresentação do bloco “Próximo passo” (contracts/guidance-derivation.md)."""

    title: str
    body: str
    cta_label: str | None = None
    cta_url_name: str | None = None
    cta_kwargs: Mapping[str, Any] = field(default_factory=dict)
    blocked_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, 'cta_kwargs', dict(self.cta_kwargs))
        if self.cta_url_name is None:
            if self.cta_label is not None:
                raise ValueError(
                    'cta_label exige cta_url_name; use ambos None quando sem CTA.'
                )
            return
        if self.cta_url_name not in ALLOWED_CTA_URL_NAMES:
            raise ValueError(
                f'cta_url_name fora da allowlist: {self.cta_url_name!r}'
            )
        if self.cta_label is None:
            raise ValueError('cta_url_name exige cta_label não-nulo.')


@dataclass(frozen=True)
class StageStep:
    """Uma etapa do stepper visual (marcação, não máquina de estados)."""

    key: str
    label: str
    state: StageVisualState

    def __post_init__(self) -> None:
        if self.key not in STAGE_LABELS:
            raise ValueError(f'key de etapa inválida: {self.key!r}')
        if self.state not in ('concluida', 'atual', 'futura', 'bloqueada'):
            raise ValueError(f'state visual inválido: {self.state!r}')


@dataclass(frozen=True)
class StageStepperState:
    """DTO do stepper das 6 etapas (data-model.md / FR-002)."""

    stages: tuple[StageStep, ...]

    def __post_init__(self) -> None:
        stages = tuple(self.stages)
        object.__setattr__(self, 'stages', stages)
        keys = tuple(step.key for step in stages)
        if keys != STAGE_ORDER:
            raise ValueError(
                'stages deve listar exatamente as 6 etapas na ordem canônica; '
                f'recebido {keys!r}.'
            )


def _pk_kwargs(pk: int | None) -> dict[str, int]:
    return {'pk': pk} if pk is not None else {}


def _uniform_stepper(state: StageVisualState) -> StageStepperState:
    return StageStepperState(
        stages=tuple(
            StageStep(key=key, label=STAGE_LABELS[key], state=state)
            for key in STAGE_ORDER
        )
    )


def _normalize_blocked_keys(
    blocked_keys: Collection[str] | None,
) -> frozenset[str]:
    if not blocked_keys:
        return frozenset()
    unknown = set(blocked_keys) - set(STAGE_ORDER)
    if unknown:
        raise ValueError(f'blocked_keys contém etapas inválidas: {sorted(unknown)!r}')
    return frozenset(blocked_keys)


def build_stage_stepper(
    *,
    etapa: str | None = None,
    has_open_ciclo: bool = True,
    vinculo_pendente: bool = False,
    concluida: bool = False,
    blocked_keys: Collection[str] | None = None,
) -> StageStepperState:
    """Monta ``StageStepperState`` só com marcação visual (sem mutators de stage).

    Precedência dos estados especiais (espelha ``resolve_next_step``):
    sem ciclo → vínculo pendente → concluída → progresso pela ``etapa`` atual.

    ``blocked_keys`` marca etapas futuras como ``bloqueada`` quando o caller já
    possui predicado/flag de impedimento exposto (nunca chama ``can_advance`` /
    ``advance_stage``). Etapas ``concluida`` / ``atual`` não são rebaixadas.
    """
    blocked = _normalize_blocked_keys(blocked_keys)

    if not has_open_ciclo or vinculo_pendente:
        return _uniform_stepper('bloqueada')

    if concluida:
        return _uniform_stepper('concluida')

    if not etapa or etapa not in STAGE_LABELS:
        # Sem etapa conhecida: não inventar progresso; tudo bloqueado visualmente.
        return _uniform_stepper('bloqueada')

    current_idx = STAGE_ORDER.index(etapa)
    stages: list[StageStep] = []
    for idx, key in enumerate(STAGE_ORDER):
        if idx < current_idx:
            visual: StageVisualState = 'concluida'
        elif idx == current_idx:
            visual = 'atual'
        elif key in blocked:
            visual = 'bloqueada'
        else:
            visual = 'futura'
        stages.append(StageStep(key=key, label=STAGE_LABELS[key], state=visual))

    return StageStepperState(stages=tuple(stages))


def _guidance(
    title: str,
    body: str,
    *,
    cta_label: str | None = None,
    cta_url_name: str | None = None,
    cta_kwargs: Mapping[str, Any] | None = None,
    blocked_reason: str | None = None,
) -> NextStepGuidance:
    return NextStepGuidance(
        title=title,
        body=body,
        cta_label=cta_label,
        cta_url_name=cta_url_name,
        cta_kwargs=dict(cta_kwargs or {}),
        blocked_reason=blocked_reason,
    )


def _resolve_special(
    *,
    role: str,
    has_open_ciclo: bool,
    vinculo_pendente: bool,
    concluida: bool,
    avaliacao_pk: int | None,
) -> NextStepGuidance | None:
    if not has_open_ciclo:
        return _guidance(
            'Sem ciclo em andamento',
            'Não há ciclo de desempenho aberto no momento.',
            blocked_reason='Nenhum ciclo aberto.',
        )

    if vinculo_pendente:
        # Soft CTA opcional no painel (contrato: — ou Ver painel).
        if role == 'colaborador':
            return _guidance(
                'Avaliação ainda não vinculada',
                (
                    'Seu vínculo ao ciclo ainda não está pronto; '
                    'acompanhe com o RH se necessário.'
                ),
                cta_label='Ver painel',
                cta_url_name='dashboard:personal',
                blocked_reason='Vínculo ou avaliação ainda pendente.',
            )
        return _guidance(
            'Avaliação ainda não vinculada',
            (
                'Há vínculo ou avaliação pendente no ciclo aberto; '
                'aguarde a vinculação antes de orientar avanço de etapa.'
            ),
            blocked_reason='Vínculo ou avaliação ainda pendente.',
        )

    if concluida:
        kwargs = _pk_kwargs(avaliacao_pk)
        if avaliacao_pk is not None:
            return _guidance(
                'Ciclo concluído para você',
                'Não há próxima ação de etapa nesta avaliação.',
                cta_label='Ver avaliação',
                cta_url_name='reviews:detail',
                cta_kwargs=kwargs,
            )
        return _guidance(
            'Ciclo concluído para você',
            'Não há próxima ação de etapa nesta avaliação.',
            blocked_reason='Avaliação concluída; sem próxima ação de etapa.',
        )

    return None


def _resolve_etapa_colaborador(
    etapa: str,
    *,
    avaliacao_pk: int | None,
    feedback_pk: int | None,
) -> NextStepGuidance | None:
    if etapa == ETAPA_INPUT_METAS:
        return _guidance(
            'Defina suas metas',
            (
                'Cadastre e ajuste as metas deste ciclo antes de enviar '
                'para aprovação.'
            ),
            cta_label='Ir para metas',
            cta_url_name='goals:meta_list',
        )
    if etapa == ETAPA_APROVACAO_METAS:
        return _guidance(
            'Metas em aprovação',
            (
                'Aguarde a decisão do líder; se houver reprovação, '
                'corrija e reenvie.'
            ),
            cta_label='Ver metas',
            cta_url_name='goals:meta_list',
            blocked_reason='Aguardando decisão do líder sobre as metas.',
        )
    if etapa == ETAPA_RESULTADOS:
        return _guidance(
            'Atualize os resultados',
            'Informe o progresso/resultados das metas deste ciclo.',
            cta_label='Atualizar resultados',
            cta_url_name='goals:meta_list',
        )
    if etapa == ETAPA_APROVACAO_RESULTADOS:
        return _guidance(
            'Resultados em aprovação',
            (
                'Aguarde a decisão do líder; se houver reprovação, '
                'corrija o progresso e reenvie.'
            ),
            cta_label='Ver resultados',
            cta_url_name='goals:meta_list',
            blocked_reason='Aguardando decisão do líder sobre os resultados.',
        )
    if etapa == ETAPA_AVALIACAO:
        kwargs = _pk_kwargs(avaliacao_pk)
        if avaliacao_pk is None:
            return _guidance(
                'Faça a autoavaliação',
                'Preencha as notas das competências na sua avaliação.',
                blocked_reason='Avaliação ainda sem identificador para o CTA.',
            )
        return _guidance(
            'Faça a autoavaliação',
            'Preencha as notas das competências na sua avaliação.',
            cta_label='Autoavaliar',
            cta_url_name='reviews:self_assessment',
            cta_kwargs=kwargs,
        )
    if etapa == ETAPA_FEEDBACK:
        if feedback_pk is not None:
            return _guidance(
                'Confirme ciência do feedback',
                (
                    'Leia o feedback e registre ciência quando a regra '
                    'atual permitir.'
                ),
                cta_label='Dar ciência',
                cta_url_name='reviews:feedback_acknowledge',
                cta_kwargs={'pk': feedback_pk},
            )
        kwargs = _pk_kwargs(avaliacao_pk)
        if avaliacao_pk is not None:
            return _guidance(
                'Confirme ciência do feedback',
                (
                    'Leia o feedback e registre ciência quando a regra '
                    'atual permitir.'
                ),
                cta_label='Dar ciência',
                cta_url_name='reviews:feedback_list',
                cta_kwargs=kwargs,
                blocked_reason=(
                    'Feedback específico ainda não informado; '
                    'abra a lista da avaliação.'
                ),
            )
        return _guidance(
            'Confirme ciência do feedback',
            (
                'Leia o feedback e registre ciência quando a regra '
                'atual permitir.'
            ),
            blocked_reason='Aguardando feedback elegível para ciência.',
        )
    return None


def _resolve_etapa_lider(
    etapa: str,
    *,
    avaliacao_pk: int | None,
) -> NextStepGuidance | None:
    if etapa == ETAPA_INPUT_METAS:
        return _guidance(
            'Aguardando metas do time',
            (
                'Os colaboradores do seu escopo ainda estão na etapa '
                'de input de metas.'
            ),
            cta_label='Ver time',
            cta_url_name='dashboard:team',
            blocked_reason='Colaboradores ainda na etapa de input de metas.',
        )
    if etapa == ETAPA_APROVACAO_METAS:
        return _guidance(
            'Aprove as metas',
            'Revise e aprove ou reprove as metas pendentes no seu escopo.',
            cta_label='Revisar metas',
            cta_url_name='goals:meta_list',
        )
    if etapa == ETAPA_RESULTADOS:
        return _guidance(
            'Aguardando resultados',
            'O time ainda registra resultados das metas.',
            cta_label='Ver metas do time',
            cta_url_name='goals:meta_list',
            blocked_reason='Colaboradores ainda registrando resultados.',
        )
    if etapa == ETAPA_APROVACAO_RESULTADOS:
        return _guidance(
            'Aprove os resultados',
            'Revise e aprove ou reprove os resultados pendentes.',
            cta_label='Revisar resultados',
            cta_url_name='goals:meta_list',
        )
    if etapa == ETAPA_AVALIACAO:
        kwargs = _pk_kwargs(avaliacao_pk)
        if avaliacao_pk is None:
            return _guidance(
                'Avalie o colaborador',
                'Preencha as notas de competências do liderado nesta etapa.',
                blocked_reason='Avaliação ainda sem identificador para o CTA.',
            )
        return _guidance(
            'Avalie o colaborador',
            'Preencha as notas de competências do liderado nesta etapa.',
            cta_label='Avaliar',
            cta_url_name='reviews:leader_assessment',
            cta_kwargs=kwargs,
        )
    if etapa == ETAPA_FEEDBACK:
        kwargs = _pk_kwargs(avaliacao_pk)
        if avaliacao_pk is None:
            return _guidance(
                'Registre o feedback',
                (
                    'Conduza o feedback da avaliação quando elegível '
                    'pelas regras atuais.'
                ),
                blocked_reason='Avaliação ainda sem identificador para o CTA.',
            )
        return _guidance(
            'Registre o feedback',
            (
                'Conduza o feedback da avaliação quando elegível '
                'pelas regras atuais.'
            ),
            cta_label='Ir ao feedback',
            cta_url_name='reviews:feedback_create',
            cta_kwargs=kwargs,
        )
    return None


def _resolve_etapa_rh(
    etapa: str,
    *,
    avaliacao_pk: int | None,
) -> NextStepGuidance:
    """RH não é ator de etapa: copy de acompanhamento sem inventar avanço."""
    kwargs = _pk_kwargs(avaliacao_pk)
    etapa_label = etapa.replace('_', ' ')
    if avaliacao_pk is not None:
        return _guidance(
            'Acompanhe o ciclo',
            f'A avaliação está na etapa de {etapa_label}; ação cabe aos atores.',
            cta_label='Ver avaliação',
            cta_url_name='reviews:detail',
            cta_kwargs=kwargs,
            blocked_reason='Papel RH sem CTA de avanço de etapa.',
        )
    return _guidance(
        'Acompanhe o ciclo',
        f'Há avaliações na etapa de {etapa_label}; ação cabe aos atores.',
        blocked_reason='Papel RH sem CTA de avanço de etapa.',
    )


def resolve_next_step(
    *,
    role: GuidanceRole | str,
    etapa: str | None = None,
    avaliacao_pk: int | None = None,
    feedback_pk: int | None = None,
    has_open_ciclo: bool = True,
    vinculo_pendente: bool = False,
    concluida: bool = False,
) -> NextStepGuidance:
    """Deriva ``NextStepGuidance`` do estado já existente (somente leitura).

    Papel e flags entram explícitos (testável sem AuthZ/DB). Destinos de CTA
    restritos a ``ALLOWED_CTA_URL_NAMES``.

    Precedência dos estados especiais: sem ciclo → vínculo pendente → concluída
    → mapa ``etapa × papel``.
    """
    role_norm = str(role).strip().lower()
    if role_norm not in ('colaborador', 'lider', 'rh'):
        raise ValueError(
            f'role inválido: {role!r}; use colaborador|lider|rh.'
        )

    special = _resolve_special(
        role=role_norm,
        has_open_ciclo=has_open_ciclo,
        vinculo_pendente=vinculo_pendente,
        concluida=concluida,
        avaliacao_pk=avaliacao_pk,
    )
    if special is not None:
        return special

    if not etapa:
        return _guidance(
            'Sem etapa atual',
            'Não foi possível determinar a etapa da avaliação.',
            blocked_reason='Etapa ausente no contexto de orientação.',
        )

    if role_norm == 'colaborador':
        resolved = _resolve_etapa_colaborador(
            etapa,
            avaliacao_pk=avaliacao_pk,
            feedback_pk=feedback_pk,
        )
    elif role_norm == 'lider':
        resolved = _resolve_etapa_lider(etapa, avaliacao_pk=avaliacao_pk)
    else:
        resolved = _resolve_etapa_rh(etapa, avaliacao_pk=avaliacao_pk)

    if resolved is not None:
        return resolved

    return _guidance(
        'Etapa desconhecida',
        'A etapa atual não possui orientação de apresentação mapeada.',
        blocked_reason=f'Etapa não mapeada: {etapa!r}.',
    )
