"""Seed de simulação — equipe Tecnologia (15 colaboradores) sob um gestor.

Cria um ciclo dedicado ``[SIM]``, catálogo mínimo e cenários ricos em etapas
diferentes para validar dashboards, guidance, badge de pendências e PDI.

Marca tudo com ``[SIM]`` / e-mails ``@sim.greenn.local`` para remoção limpa.

Uso (Docker):
  docker compose up -d
  docker compose exec -T web python scripts/seed_sim_tech_team.py \\
      --gestor gestor@greenn.com.br
  docker compose exec -T web python scripts/seed_sim_tech_team.py --purge

Não altera a senha do gestor. Colaboradores simulados: ``TestPass123!``.

Atenção: só pode haver um ciclo aberto; o seed encerra o ciclo aberto atual
(se houver) e abre o ciclo ``[SIM]``. O id do ciclo encerrado é impresso.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

import django

django.setup()

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.competencies.models import CargoCompetencia, Competencia, Escala
from apps.competencies.services.catalog_import.importer import resolve_default_escala
from apps.cycles.models import Ciclo
from apps.cycles.services.cycle import close_cycle, open_cycle
from apps.cycles.services.stage import advance_stage
from apps.goals.models import Meta, ObjetivoEstrategico
from apps.goals.services.approval import (
    approve_meta,
    approve_resultado,
    reject_meta,
    reject_resultado,
)
from apps.organization.models import Area, Cargo
from apps.pdi.models import AcaoPDI, PDI
from apps.reviews.models import Avaliacao, AvaliacaoCompetencia, Feedback
from apps.reviews.services.evaluation import (
    calcular_nota_final_autoavaliacao,
    calcular_nota_final_lider,
)
from apps.talent.services.classification import upsert_classification

# ---------------------------------------------------------------------------
# Constantes / tags
# ---------------------------------------------------------------------------

TAG = '[SIM]'
EMAIL_DOMAIN = 'sim.greenn.local'
PASSWORD_SIM = 'TestPass123!'
DEFAULT_GESTOR = 'gestor@greenn.com.br'
AREA_NOME_CANONICO = 'TECNOLOGIA'  # nome já usado no ambiente do usuário
CICLO_NOME = f'{TAG} Ciclo Tecnologia Demo'
OBJETIVO_DESC = f'{TAG} Objetivo Estratégico — evolução contínua do produto'

CARGO_SPECS = (
    (f'{TAG} Desenvolvedor Júnior', 2),
    (f'{TAG} Desenvolvedor Pleno', 3),
    (f'{TAG} Desenvolvedor Sênior', 4),
    (f'{TAG} Tech Lead', 5),
)

COMP_SPECS = (
    (f'{TAG} Python / Django', Competencia.Tipo.TECNICA, '3.00'),
    (f'{TAG} Trabalho em equipe', Competencia.Tipo.COMPORTAMENTAL, '3.00'),
    (f'{TAG} Entrega e ownership', Competencia.Tipo.COMPORTAMENTAL, '4.00'),
)


def _sim_email(n: int) -> str:
    return f'sim{n:02d}.tech@{EMAIL_DOMAIN}'


COLABS: list[dict] = [
    {
        'n': 1,
        'nome': f'{TAG} Ana Souza',
        'cargo_idx': 0,
        'cenario': 'input_sem_meta',
        'resumo': 'input_metas · sem meta (próximo passo: criar meta)',
    },
    {
        'n': 2,
        'nome': f'{TAG} Bruno Lima',
        'cargo_idx': 0,
        'cenario': 'input_com_meta',
        'resumo': 'input_metas · 1 meta (apto a avançar)',
    },
    {
        'n': 3,
        'nome': f'{TAG} Carla Mendes',
        'cargo_idx': 1,
        'cenario': 'aprovacao_reprovada',
        'resumo': 'aprovacao_metas · meta REPROVADA (pós-rejeição)',
    },
    {
        'n': 4,
        'nome': f'{TAG} Diego Alves',
        'cargo_idx': 1,
        'cenario': 'aprovacao_pendente',
        'resumo': 'aprovacao_metas · metas pendentes (badge líder)',
    },
    {
        'n': 5,
        'nome': f'{TAG} Elena Rocha',
        'cargo_idx': 1,
        'cenario': 'aprovacao_parcial',
        'resumo': 'aprovacao_metas · 1 aprovada + 1 pendente',
    },
    {
        'n': 6,
        'nome': f'{TAG} Felipe Castro',
        'cargo_idx': 2,
        'cenario': 'resultados_sem_progresso',
        'resumo': 'resultados · progresso ainda vazio',
    },
    {
        'n': 7,
        'nome': f'{TAG} Gabriela Nunes',
        'cargo_idx': 2,
        'cenario': 'resultados_com_progresso',
        'resumo': 'resultados · progresso preenchido (apto a avançar)',
    },
    {
        'n': 8,
        'nome': f'{TAG} Henrique Dias',
        'cargo_idx': 2,
        'cenario': 'aprovacao_resultados_pendente',
        'resumo': 'aprovacao_resultados · aguardando líder',
    },
    {
        'n': 9,
        'nome': f'{TAG} Isabela Freitas',
        'cargo_idx': 2,
        'cenario': 'aprovacao_resultados_reprovado',
        'resumo': 'aprovacao_resultados · resultado REPROVADO',
    },
    {
        'n': 10,
        'nome': f'{TAG} João Ribeiro',
        'cargo_idx': 3,
        'cenario': 'avaliacao_sem_notas',
        'resumo': 'avaliacao · linhas sem nota do líder (badge)',
    },
    {
        'n': 11,
        'nome': f'{TAG} Karin Oliveira',
        'cargo_idx': 1,
        'cenario': 'avaliacao_com_auto',
        'resumo': 'avaliacao · autoavaliação preenchida; líder parcial',
    },
    {
        'n': 12,
        'nome': f'{TAG} Lucas Martins',
        'cargo_idx': 2,
        'cenario': 'feedback_aguardando_ciente',
        'resumo': 'feedback · feedback do líder; sem ciência',
    },
    {
        'n': 13,
        'nome': f'{TAG} Marina Costa',
        'cargo_idx': 3,
        'cenario': 'feedback_concluido_pdi_9box',
        'resumo': 'feedback concluído + PDI + 9-box',
    },
    {
        'n': 14,
        'nome': f'{TAG} Nicolas Teixeira',
        'cargo_idx': 0,
        'cenario': 'feedback_pdi_atrasado',
        'resumo': 'feedback concluído + PDI com ação ATRASADA',
    },
    {
        'n': 15,
        'nome': f'{TAG} Olivia Barbosa',
        'cargo_idx': 3,
        'cenario': 'top_performer',
        'resumo': 'feedback concluído · notas altas · 9-box alto',
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def upsert_sim_user(*, email: str, password: str, **kwargs) -> CustomUser:
    user = CustomUser.objects.filter(email=email).first()
    if user is None:
        return CustomUser.objects.create_user(email=email, password=password, **kwargs)
    for key, value in kwargs.items():
        setattr(user, key, value)
    user.set_password(password)
    user.save()
    return user


def load_gestor(email: str) -> CustomUser:
    gestor = CustomUser.objects.filter(email=email).select_related('area', 'cargo').first()
    if gestor is None:
        raise SystemExit(
            f'Gestor não encontrado: {email!r}. Crie a conta antes ou passe --gestor.',
        )
    if not gestor.is_active:
        raise SystemExit(f'Gestor {email!r} está inativo.')
    if gestor.email_confirmado_em is None:
        gestor.email_confirmado_em = timezone.now()
        gestor.save(update_fields=['email_confirmado_em'])
    return gestor


def ensure_area_for_gestor(gestor: CustomUser) -> Area:
    """Reusa a área do gestor; senão localiza/cria TECNOLOGIA (case-insensitive)."""
    if gestor.area_id is not None and gestor.area.is_active:
        return gestor.area

    area = (
        Area.objects.filter(is_active=True, nome__iexact=AREA_NOME_CANONICO).first()
        or Area.objects.filter(nome__iexact=AREA_NOME_CANONICO).first()
    )
    if area is None:
        area = Area.objects.create(nome=AREA_NOME_CANONICO, is_active=True)
    elif not area.is_active:
        area.is_active = True
        area.save(update_fields=['is_active'])

    gestor.area = area
    gestor.save(update_fields=['area'])
    return area


def ensure_cargos_e_competencias() -> tuple[list[Cargo], list[Competencia]]:
    escala = resolve_default_escala()
    cargos: list[Cargo] = []
    for nome, nivel in CARGO_SPECS:
        cargo, _ = Cargo.objects.get_or_create(
            nome=nome,
            defaults={'nivel': nivel, 'is_active': True},
        )
        if not cargo.is_active:
            cargo.is_active = True
            cargo.nivel = nivel
            cargo.save(update_fields=['is_active', 'nivel'])
        cargos.append(cargo)

    competencias: list[Competencia] = []
    for nome, tipo, _nivel in COMP_SPECS:
        comp, _ = Competencia.objects.get_or_create(
            nome=nome,
            defaults={
                'tipo': tipo,
                'escala': escala,
                'descricao': f'Competência de simulação {TAG}',
                'is_active': True,
            },
        )
        if not comp.is_active:
            comp.is_active = True
            comp.save(update_fields=['is_active'])
        competencias.append(comp)

    for cargo, (_cn, nivel_cargo) in zip(cargos, CARGO_SPECS, strict=True):
        for comp, (_pn, _t, nivel_esp) in zip(competencias, COMP_SPECS, strict=True):
            # Sênior/Lead: espera um pouco mais.
            esperado = Decimal(nivel_esp)
            if nivel_cargo >= 4:
                esperado = min(Decimal('5.00'), esperado + Decimal('1.00'))
            CargoCompetencia.objects.update_or_create(
                cargo=cargo,
                competencia=comp,
                defaults={
                    'nivel_esperado': esperado,
                    'peso': Decimal('1.00'),
                },
            )
    return cargos, competencias


def ensure_sim_ciclo() -> tuple[Ciclo, int | None]:
    """Fecha ciclo aberto atual (se houver), reutiliza/cria o ciclo [SIM] e abre."""
    closed_id: int | None = None
    for aberto in Ciclo.objects.filter(status=Ciclo.Status.ABERTO):
        if aberto.nome == CICLO_NOME:
            continue
        close_cycle(aberto)
        closed_id = aberto.pk
        print(f'AVISO: ciclo aberto id={aberto.pk} nome={aberto.nome!r} foi encerrado.')

    today = date.today()
    ciclo = Ciclo.objects.filter(nome=CICLO_NOME).first()
    if ciclo is None:
        ciclo = Ciclo.objects.create(
            nome=CICLO_NOME,
            data_inicio=today - timedelta(days=45),
            data_fim=today + timedelta(days=75),
            status=Ciclo.Status.ENCERRADO,
        )
    if ciclo.status != Ciclo.Status.ABERTO:
        # Se outro [SIM] ficou aberto, close first (shouldn't happen).
        for aberto in Ciclo.objects.filter(status=Ciclo.Status.ABERTO).exclude(pk=ciclo.pk):
            close_cycle(aberto)
            closed_id = closed_id or aberto.pk
        open_cycle(ciclo)
    ciclo.refresh_from_db()
    return ciclo, closed_id


def get_avaliacao(ciclo: Ciclo, user: CustomUser) -> Avaliacao:
    return Avaliacao.objects.get(ciclo=ciclo, usuario=user)


def ensure_meta(user: CustomUser, objetivo: ObjetivoEstrategico, descricao: str) -> Meta:
    meta = Meta.objects.filter(
        usuario=user,
        objetivo_estrategico=objetivo,
        descricao=descricao,
    ).first()
    if meta is None:
        meta = Meta.objects.create(
            usuario=user,
            objetivo_estrategico=objetivo,
            descricao=descricao,
        )
    return meta


def ensure_pdi(
    user: CustomUser,
    *,
    titulo: str,
    acoes: list[dict],
) -> PDI:
    pdi, _ = PDI.objects.get_or_create(
        usuario=user,
        titulo=titulo,
        defaults={'status': PDI.Status.ATIVO},
    )
    for spec in acoes:
        exists = AcaoPDI.objects.filter(pdi=pdi, descricao=spec['descricao']).exists()
        if exists:
            continue
        AcaoPDI.objects.create(
            pdi=pdi,
            descricao=spec['descricao'],
            responsavel=spec['responsavel'],
            prazo=spec['prazo'],
            status=spec.get('status', AcaoPDI.Status.PENDENTE),
        )
    return pdi


# ---------------------------------------------------------------------------
# Cenários (avançam via serviços de domínio)
# ---------------------------------------------------------------------------


def _to_aprovacao_com_metas(
    av: Avaliacao,
    user: CustomUser,
    objetivo: ObjetivoEstrategico,
    descricoes: list[str],
) -> list[Meta]:
    metas = [ensure_meta(user, objetivo, d) for d in descricoes]
    av.refresh_from_db()
    if av.etapa == Avaliacao.Etapa.INPUT_METAS:
        advance_stage(av, user)
        av.refresh_from_db()
    return metas


def _approve_all_and_to_resultados(
    av: Avaliacao,
    lider: CustomUser,
    metas: list[Meta],
) -> None:
    for meta in metas:
        meta.refresh_from_db()
        if meta.status == Meta.Status.PENDENTE:
            approve_meta(meta, lider)
    av.refresh_from_db()
    if av.etapa == Avaliacao.Etapa.APROVACAO_METAS:
        advance_stage(av, lider)
        av.refresh_from_db()


def _set_progresso(metas: list[Meta], valores: list[Decimal]) -> None:
    for meta, valor in zip(metas, valores, strict=True):
        meta.progresso = valor
        meta.save(update_fields=['progresso', 'updated_at'])


def _to_aprovacao_resultados(av: Avaliacao, actor: CustomUser) -> None:
    av.refresh_from_db()
    if av.etapa == Avaliacao.Etapa.RESULTADOS:
        advance_stage(av, actor)
        av.refresh_from_db()


def _approve_resultados_and_to_avaliacao(
    av: Avaliacao,
    lider: CustomUser,
    metas: list[Meta],
) -> None:
    for meta in metas:
        meta.refresh_from_db()
        if meta.status_resultado == Meta.StatusResultado.PENDENTE:
            approve_resultado(meta, lider)
    av.refresh_from_db()
    if av.etapa == Avaliacao.Etapa.APROVACAO_RESULTADOS:
        advance_stage(av, lider)
        av.refresh_from_db()


def _fill_scores(
    av: Avaliacao,
    *,
    auto: Decimal | None,
    lider_nota: Decimal | None,
    calc_auto: bool = True,
    calc_lider: bool = True,
) -> None:
    linhas = list(AvaliacaoCompetencia.objects.filter(avaliacao=av))
    for linha in linhas:
        fields: list[str] = []
        if auto is not None and linha.nota_autoavaliacao is None:
            linha.nota_autoavaliacao = auto
            fields.append('nota_autoavaliacao')
        if lider_nota is not None and linha.nota_lider is None:
            linha.nota_lider = lider_nota
            fields.append('nota_lider')
        if fields:
            linha.save(update_fields=[*fields, 'updated_at'])
    if calc_auto and auto is not None:
        calcular_nota_final_autoavaliacao(av)
    if calc_lider and lider_nota is not None:
        calcular_nota_final_lider(av)
    av.refresh_from_db()


def _to_feedback(av: Avaliacao, actor: CustomUser) -> None:
    av.refresh_from_db()
    if av.etapa == Avaliacao.Etapa.AVALIACAO:
        advance_stage(av, actor)
        av.refresh_from_db()


def _ensure_feedback_lider(
    av: Avaliacao,
    lider: CustomUser,
    conteudo: str,
    *,
    ciente: bool,
) -> Feedback:
    fb = (
        Feedback.objects.filter(avaliacao=av, tipo=Feedback.Tipo.LIDER, autor=lider)
        .order_by('-pk')
        .first()
    )
    if fb is None:
        fb = Feedback.objects.create(
            avaliacao=av,
            autor=lider,
            tipo=Feedback.Tipo.LIDER,
            conteudo=conteudo,
            ciente_em=timezone.now() if ciente else None,
        )
    elif ciente and fb.ciente_em is None:
        fb.ciente_em = timezone.now()
        fb.save(update_fields=['ciente_em', 'updated_at'])
    if ciente:
        av.refresh_from_db()
        if not av.concluida:
            advance_stage(av, lider)  # marca concluida se pré-conds ok
            av.refresh_from_db()
    return fb


def apply_cenario(
    *,
    spec: dict,
    user: CustomUser,
    ciclo: Ciclo,
    objetivo: ObjetivoEstrategico,
    gestor: CustomUser,
    admin: CustomUser | None,
) -> str:
    av = get_avaliacao(ciclo, user)
    cenario = spec['cenario']
    today = date.today()
    base = f'{TAG} Meta de {user.nome.split("] ")[-1]}'

    if cenario == 'input_sem_meta':
        return Avaliacao.Etapa.INPUT_METAS

    if cenario == 'input_com_meta':
        ensure_meta(user, objetivo, f'{base} — entregar feature X')
        return Avaliacao.Etapa.INPUT_METAS

    if cenario == 'aprovacao_reprovada':
        metas = _to_aprovacao_com_metas(av, user, objetivo, [f'{base} — revisão arquitetural'])
        if metas[0].status == Meta.Status.PENDENTE:
            reject_meta(metas[0], gestor)
        return Avaliacao.Etapa.APROVACAO_METAS

    if cenario == 'aprovacao_pendente':
        _to_aprovacao_com_metas(
            av,
            user,
            objetivo,
            [
                f'{base} — reduzir latência API',
                f'{base} — cobrir testes críticos',
            ],
        )
        return Avaliacao.Etapa.APROVACAO_METAS

    if cenario == 'aprovacao_parcial':
        metas = _to_aprovacao_com_metas(
            av,
            user,
            objetivo,
            [f'{base} — OKR Q consolidado', f'{base} — mentoria de júnior'],
        )
        if metas[0].status == Meta.Status.PENDENTE:
            approve_meta(metas[0], gestor)
        return Avaliacao.Etapa.APROVACAO_METAS

    if cenario == 'resultados_sem_progresso':
        metas = _to_aprovacao_com_metas(av, user, objetivo, [f'{base} — migration zero-downtime'])
        _approve_all_and_to_resultados(av, gestor, metas)
        return Avaliacao.Etapa.RESULTADOS

    if cenario == 'resultados_com_progresso':
        metas = _to_aprovacao_com_metas(av, user, objetivo, [f'{base} — painel de métricas'])
        _approve_all_and_to_resultados(av, gestor, metas)
        _set_progresso(metas, [Decimal('75.00')])
        return Avaliacao.Etapa.RESULTADOS

    if cenario == 'aprovacao_resultados_pendente':
        metas = _to_aprovacao_com_metas(av, user, objetivo, [f'{base} — liberar módulo billing'])
        _approve_all_and_to_resultados(av, gestor, metas)
        _set_progresso(metas, [Decimal('90.00')])
        _to_aprovacao_resultados(av, user)
        return Avaliacao.Etapa.APROVACAO_RESULTADOS

    if cenario == 'aprovacao_resultados_reprovado':
        metas = _to_aprovacao_com_metas(av, user, objetivo, [f'{base} — SLA 99.9%'])
        _approve_all_and_to_resultados(av, gestor, metas)
        _set_progresso(metas, [Decimal('40.00')])
        _to_aprovacao_resultados(av, user)
        metas[0].refresh_from_db()
        if metas[0].status_resultado == Meta.StatusResultado.PENDENTE:
            reject_resultado(metas[0], gestor)
        return Avaliacao.Etapa.APROVACAO_RESULTADOS

    if cenario == 'avaliacao_sem_notas':
        metas = _to_aprovacao_com_metas(av, user, objetivo, [f'{base} — liderar squad checkout'])
        _approve_all_and_to_resultados(av, gestor, metas)
        _set_progresso(metas, [Decimal('85.00')])
        _to_aprovacao_resultados(av, user)
        _approve_resultados_and_to_avaliacao(av, gestor, metas)
        return Avaliacao.Etapa.AVALIACAO

    if cenario == 'avaliacao_com_auto':
        metas = _to_aprovacao_com_metas(av, user, objetivo, [f'{base} — onboarding tech'])
        _approve_all_and_to_resultados(av, gestor, metas)
        _set_progresso(metas, [Decimal('70.00')])
        _to_aprovacao_resultados(av, user)
        _approve_resultados_and_to_avaliacao(av, gestor, metas)
        _fill_scores(av, auto=Decimal('4.00'), lider_nota=None, calc_lider=False)
        # Uma nota parcial do líder em só a 1ª linha — deixa pendência realista.
        primeira = AvaliacaoCompetencia.objects.filter(avaliacao=av).order_by('pk').first()
        if primeira and primeira.nota_lider is None:
            primeira.nota_lider = Decimal('3.00')
            primeira.save(update_fields=['nota_lider', 'updated_at'])
        return Avaliacao.Etapa.AVALIACAO

    if cenario == 'feedback_aguardando_ciente':
        metas = _to_aprovacao_com_metas(av, user, objetivo, [f'{base} — feature flags'])
        _approve_all_and_to_resultados(av, gestor, metas)
        _set_progresso(metas, [Decimal('80.00')])
        _to_aprovacao_resultados(av, user)
        _approve_resultados_and_to_avaliacao(av, gestor, metas)
        _fill_scores(av, auto=Decimal('4.00'), lider_nota=Decimal('4.00'))
        _to_feedback(av, gestor)
        _ensure_feedback_lider(
            av,
            gestor,
            f'{TAG} Bom ciclo. Foque em comunicação com stakeholders.',
            ciente=False,
        )
        return Avaliacao.Etapa.FEEDBACK

    if cenario == 'feedback_concluido_pdi_9box':
        metas = _to_aprovacao_com_metas(av, user, objetivo, [f'{base} — plataforma de observabilidade'])
        _approve_all_and_to_resultados(av, gestor, metas)
        _set_progresso(metas, [Decimal('95.00')])
        _to_aprovacao_resultados(av, user)
        _approve_resultados_and_to_avaliacao(av, gestor, metas)
        _fill_scores(av, auto=Decimal('4.00'), lider_nota=Decimal('4.00'))
        _to_feedback(av, gestor)
        _ensure_feedback_lider(
            av,
            gestor,
            f'{TAG} Excelente ownership. Próximo passo: liderança técnica.',
            ciente=True,
        )
        ensure_pdi(
            user,
            titulo=f'{TAG} PDI — liderança técnica',
            acoes=[
                {
                    'descricao': f'{TAG} Mentorar 1 júnior no semestre',
                    'responsavel': user,
                    'prazo': today + timedelta(days=45),
                    'status': AcaoPDI.Status.EM_ANDAMENTO,
                },
                {
                    'descricao': f'{TAG} Apresentar talk interna de arquitetura',
                    'responsavel': gestor,
                    'prazo': today + timedelta(days=60),
                    'status': AcaoPDI.Status.PENDENTE,
                },
            ],
        )
        if admin is not None:
            upsert_classification(user, ciclo, potencial=3, admin=admin)
        return Avaliacao.Etapa.FEEDBACK

    if cenario == 'feedback_pdi_atrasado':
        metas = _to_aprovacao_com_metas(av, user, objetivo, [f'{base} — estabilizar CI'])
        _approve_all_and_to_resultados(av, gestor, metas)
        _set_progresso(metas, [Decimal('60.00')])
        _to_aprovacao_resultados(av, user)
        _approve_resultados_and_to_avaliacao(av, gestor, metas)
        _fill_scores(av, auto=Decimal('3.00'), lider_nota=Decimal('3.00'))
        _to_feedback(av, gestor)
        _ensure_feedback_lider(
            av,
            gestor,
            f'{TAG} Progresso sólido. Cuide dos prazos das ações de PDI.',
            ciente=True,
        )
        ensure_pdi(
            user,
            titulo=f'{TAG} PDI — disciplina de entrega',
            acoes=[
                {
                    'descricao': f'{TAG} Curso de testes automatizados (atrasado)',
                    'responsavel': user,
                    'prazo': today - timedelta(days=10),
                    'status': AcaoPDI.Status.ATRASADA,
                },
            ],
        )
        if admin is not None:
            upsert_classification(user, ciclo, potencial=2, admin=admin)
        return Avaliacao.Etapa.FEEDBACK

    if cenario == 'top_performer':
        metas = _to_aprovacao_com_metas(
            av,
            user,
            objetivo,
            [
                f'{base} — redesign do core de pagamentos',
                f'{base} — reduzir MTTR em 30%',
            ],
        )
        _approve_all_and_to_resultados(av, gestor, metas)
        _set_progresso(metas, [Decimal('100.00'), Decimal('88.00')])
        _to_aprovacao_resultados(av, user)
        _approve_resultados_and_to_avaliacao(av, gestor, metas)
        _fill_scores(av, auto=Decimal('5.00'), lider_nota=Decimal('5.00'))
        _to_feedback(av, gestor)
        _ensure_feedback_lider(
            av,
            gestor,
            f'{TAG} Referência da área. Continuidade e influência no chapter.',
            ciente=True,
        )
        ensure_pdi(
            user,
            titulo=f'{TAG} PDI — influência org-wide',
            acoes=[
                {
                    'descricao': f'{TAG} Definir standards de código do chapter',
                    'responsavel': user,
                    'prazo': today + timedelta(days=30),
                    'status': AcaoPDI.Status.EM_ANDAMENTO,
                },
                {
                    'descricao': f'{TAG} Pair com Tech Lead em design review',
                    'responsavel': gestor,
                    'prazo': today + timedelta(days=20),
                    'status': AcaoPDI.Status.PENDENTE,
                },
            ],
        )
        if admin is not None:
            upsert_classification(user, ciclo, potencial=3, admin=admin)
        return Avaliacao.Etapa.FEEDBACK

    raise ValueError(f'Cenário desconhecido: {cenario}')


# ---------------------------------------------------------------------------
# Purge
# ---------------------------------------------------------------------------


def sim_users_qs():
    return CustomUser.objects.filter(email__endswith=f'@{EMAIL_DOMAIN}')


def purge(*, reopen_ciclo_id: int | None = None) -> None:
    users = list(sim_users_qs())
    user_ids = [u.pk for u in users]
    ciclo = Ciclo.objects.filter(nome=CICLO_NOME).first()

    print(f'PURGE: {len(users)} usuários simulados; ciclo={"sim" if ciclo else "ausente"}')

    with transaction.atomic():
        if ciclo is not None:
            if ciclo.status == Ciclo.Status.ABERTO:
                close_cycle(ciclo)
                ciclo.refresh_from_db()

            av_ids = list(
                Avaliacao.objects.filter(ciclo=ciclo).values_list('pk', flat=True),
            )
            Feedback.objects.filter(avaliacao_id__in=av_ids).delete()
            AvaliacaoCompetencia.objects.filter(avaliacao_id__in=av_ids).delete()
            from apps.talent.models import ClassificacaoTalento

            ClassificacaoTalento.objects.filter(ciclo=ciclo).delete()
            Avaliacao.objects.filter(ciclo=ciclo).delete()

            objetivos = ObjetivoEstrategico.objects.filter(ciclo=ciclo)
            Meta.objects.filter(objetivo_estrategico__in=objetivos).delete()
            objetivos.delete()
            ciclo.delete()

        if user_ids:
            pdis = PDI.objects.filter(usuario_id__in=user_ids)
            AcaoPDI.objects.filter(pdi__in=pdis).delete()
            # Ações em que o sim era responsável em PDI alheio (não esperado).
            AcaoPDI.objects.filter(responsavel_id__in=user_ids).delete()
            pdis.delete()

            # Metas órfãs de outros ciclos (não deveria haver).
            Meta.objects.filter(usuario_id__in=user_ids).delete()
            Feedback.objects.filter(autor_id__in=user_ids).delete()
            AvaliacaoCompetencia.objects.filter(
                avaliacao__usuario_id__in=user_ids,
            ).delete()
            Avaliacao.objects.filter(usuario_id__in=user_ids).delete()
            from apps.talent.models import ClassificacaoTalento

            ClassificacaoTalento.objects.filter(usuario_id__in=user_ids).delete()

            # Soft-desativa e remove FK que bloquearia delete; hard-delete.
            CustomUser.objects.filter(pk__in=user_ids).update(line_manager=None)
            # Pode haver PROTECT se restar referência — apagamos um a um.
            for user in CustomUser.objects.filter(pk__in=user_ids):
                user.delete()

        # Catálogo [SIM]: remove vínculos e soft-delete.
        sim_comps = Competencia.objects.filter(nome__startswith=TAG)
        CargoCompetencia.objects.filter(competencia__in=sim_comps).delete()
        CargoCompetencia.objects.filter(cargo__nome__startswith=TAG).delete()
        sim_comps.update(is_active=False)
        Cargo.objects.filter(nome__startswith=TAG).update(is_active=False)

    if reopen_ciclo_id is not None:
        alvo = Ciclo.objects.filter(pk=reopen_ciclo_id).first()
        if alvo is None:
            print(f'AVISO: ciclo id={reopen_ciclo_id} não encontrado; nada a reabrir.')
        else:
            open_cycle(alvo)
            print(f'RESTORE: ciclo id={alvo.pk} reaberto.')

    print('PURGE_OK')


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------


def seed(*, gestor_email: str, reset: bool) -> None:
    if reset and (
        sim_users_qs().exists() or Ciclo.objects.filter(nome=CICLO_NOME).exists()
    ):
        print('Reset: removendo simulação anterior…')
        purge()

    gestor = load_gestor(gestor_email)
    area = ensure_area_for_gestor(gestor)
    cargos, _comps = ensure_cargos_e_competencias()

    # Não sobrescreve cargo real do gestor (ex.: CTO). Só preenche se vazio.
    if gestor.cargo_id is None:
        gestor.cargo = cargos[-1]
        gestor.save(update_fields=['cargo'])
        print(f'Gestor sem cargo — vinculado a {cargos[-1].nome!r} (só para demo).')

    admin = CustomUser.objects.filter(is_admin=True, is_active=True).first()
    if admin is None:
        print('AVISO: nenhum admin ativo — 9-box será pulado.')

    ciclo, closed_id = ensure_sim_ciclo()
    objetivo, _ = ObjetivoEstrategico.objects.get_or_create(
        ciclo=ciclo,
        descricao=OBJETIVO_DESC,
    )

    print(f'Gestor: {gestor.email} · área={area.nome} · cargo={gestor.cargo}')
    print(f'Ciclo: id={ciclo.pk} status={ciclo.status}')
    if closed_id:
        print(f'Ciclo anterior encerrado (id={closed_id}). Reabra com --purge --reopen-ciclo {closed_id}')

    rows: list[tuple[str, str, str]] = []
    for spec in COLABS:
        email = _sim_email(spec['n'])
        cargo = cargos[spec['cargo_idx']]
        user = upsert_sim_user(
            email=email,
            password=PASSWORD_SIM,
            nome=spec['nome'],
            area=area,
            cargo=cargo,
            line_manager=gestor,
            email_confirmado_em=timezone.now(),
            is_active=True,
        )
        # open_cycle já matriculou usuários ativos no open; quem foi criado
        # depois precisa de ensure.
        from apps.reviews.services.enrollment import ensure_avaliacao_for_user

        ensure_avaliacao_for_user(user, ciclo=ciclo)
        etapa = apply_cenario(
            spec=spec,
            user=user,
            ciclo=ciclo,
            objetivo=objetivo,
            gestor=gestor,
            admin=admin,
        )
        av = get_avaliacao(ciclo, user)
        rows.append((email, av.etapa, spec['resumo']))
        print(f'  ✓ {email} → {av.etapa} · {spec["resumo"]}')

    print()
    print('SEED_OK')
    print(f'gestor={gestor.email} (senha INALTERADA)')
    print(f'colaboradores={len(rows)} senha={PASSWORD_SIM}')
    print(f'ciclo_id={ciclo.pk} nome={ciclo.nome!r}')
    print('Login sugestão gestor + dashboard time / reviews / badge pendências.')
    print('Remover depois: python scripts/seed_sim_tech_team.py --purge')


def main() -> None:
    parser = argparse.ArgumentParser(description='Seed/purge simulação equipe Tecnologia')
    parser.add_argument(
        '--gestor',
        default=DEFAULT_GESTOR,
        help=f'E-mail do gestor (default: {DEFAULT_GESTOR})',
    )
    parser.add_argument(
        '--purge',
        action='store_true',
        help='Remove todos os dados [SIM] / @sim.greenn.local',
    )
    parser.add_argument(
        '--reopen-ciclo',
        type=int,
        default=None,
        metavar='ID',
        help='Com --purge, reabre o ciclo informado após limpar a simulação',
    )
    parser.add_argument(
        '--no-reset',
        action='store_true',
        help='Não limpa simulação anterior antes de (re)popular',
    )
    args = parser.parse_args()

    if args.purge:
        purge(reopen_ciclo_id=args.reopen_ciclo)
        return

    seed(gestor_email=args.gestor, reset=not args.no_reset)


if __name__ == '__main__':
    main()
