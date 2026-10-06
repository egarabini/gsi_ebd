"""
CoordenadorState — gerencia o painel do Coordenador.

Regras de negócio:
- O Coordenador (role=3) supervisiona alunos vinculados às suas turmas
  (Turma.coordenador_id == coordenador_id).
- Também pode supervisionar alunos diretamente vinculados via User.coordenador_id.
- Pode atribuir estudos aprovados aos seus alunos.
- Acompanha o progresso individual de cada aluno.
"""
from typing import List, Optional

from sqlmodel import select
import reflex as rx

from ..models.user import User, Role, UserStatus
from ..models.study import Study, StudyAssignment, StudyStatus
from ..models.progress import Progress
from ..models.turma import Turma, TurmaMembro
from ..services.study_service import StudyService
from .auth import AuthState


class CoordenadorState(AuthState):
    # ── Listas (dict para compatibilidade com rx.foreach) ────────
    alunos: list[dict] = []
    estudos_disponiveis: list[dict] = []
    turmas: list[dict] = []

    # ── Atribuição de estudos ────────────────────────────────────
    selected_study_option: str = ""
    selected_aluno_ids: list[int] = []
    message: str = ""
    message_type: str = "info"

    # ── Métricas ─────────────────────────────────────────────────
    total_alunos: int = 0
    total_ativos: int = 0
    media_progresso: float = 0.0
    pendencias: int = 0

    # ── Filtro de busca ──────────────────────────────────────────
    search_query: str = ""

    # ── Computed vars ────────────────────────────────────────────
    @rx.var
    def media_progresso_label(self) -> str:
        return f"{self.media_progresso:.0f}%"

    @rx.var
    def study_options(self) -> list[str]:
        opts = []
        for e in self.estudos_disponiveis:
            try:
                eid = e.get("id", "") if hasattr(e, "get") else e["id"]
                etit = e.get("titulo", "") if hasattr(e, "get") else e["titulo"]
                opts.append(f"{eid}:{etit}")
            except Exception:
                pass
        return opts

    @rx.var
    def has_alunos(self) -> bool:
        return self.total_alunos > 0

    @rx.var
    def has_estudos(self) -> bool:
        return len(self.estudos_disponiveis) > 0

    # ── Carregamento ─────────────────────────────────────────────

    def load_all(self):
        """Carrega tudo de uma vez no on_load da página."""
        self.load_alunos()
        self.load_estudos()
        self.load_turmas()

    def load_alunos(self):
        """Carrega os alunos do ambiente do Coordenador.

        Hierarquia: Coordenador -> Instrutor -> Aluno. O Coordenador NAO tem
        alunos vinculados diretamente (o antigo filtro por User.coordenador_id
        trazia os INSTRUTORES dele, nao alunos). Os alunos chegam por:
          1. alunos cujo instrutor responde a este coordenador
          2. alunos membros de turmas deste coordenador
        Sempre dentro da fronteira do ambiente (tenant).
        """
        amb = self.current_user_ambiente or None
        with rx.session() as session:
            # Estrategia 1: alunos dos instrutores deste coordenador
            instrutor_ids = [u.id for u in session.exec(
                select(User).where(User.role == Role.INSTRUTOR,
                                   User.coordenador_id == self.current_user_id)
            ).all()]
            alunos_diretos = []
            if instrutor_ids:
                alunos_diretos = session.exec(
                    select(User).where(
                        User.role == Role.ALUNO,
                        User.instrutor_id.in_(instrutor_ids),
                    )
                ).all()

            # Estrategia 2: via turmas do coordenador
            turma_ids_raw = session.exec(
                select(Turma.id).where(
                    Turma.coordenador_id == self.current_user_id,
                    Turma.is_active == True,
                )
            ).all()
            alunos_turma = []
            if turma_ids_raw:
                membros = session.exec(
                    select(TurmaMembro).where(
                        TurmaMembro.turma_id.in_(turma_ids_raw),
                        TurmaMembro.is_active == True,
                    )
                ).all()
                aluno_ids = list({m.user_id for m in membros})
                if aluno_ids:
                    alunos_turma = session.exec(
                        select(User).where(
                            User.id.in_(aluno_ids),
                            User.role == Role.ALUNO,
                        )
                    ).all()

            # Unifica sem duplicatas
            todos = {u.id: u for u in alunos_diretos + alunos_turma}
            alunos_list = list(todos.values())

            # Busca progresso de cada aluno (dentro do ambiente)
            aluno_ids_final = [u.id for u in alunos_list]
            progressos_raw = {}
            atribuicoes_raw = {}
            if aluno_ids_final:
                prog_stmt = select(Progress).where(Progress.user_id.in_(aluno_ids_final))
                if amb is not None:
                    prog_stmt = prog_stmt.where(Progress.ambiente_id == amb)
                for p in session.exec(prog_stmt).all():
                    if p.user_id not in progressos_raw or p.score > progressos_raw[p.user_id]:
                        progressos_raw[p.user_id] = p.score

                asg_stmt = select(StudyAssignment).where(
                    StudyAssignment.user_id.in_(aluno_ids_final),
                )
                if amb is not None:
                    asg_stmt = asg_stmt.where(StudyAssignment.ambiente_id == amb)
                assigns = session.exec(asg_stmt).all()
                for a in assigns:
                    atribuicoes_raw.setdefault(a.user_id, {"total": 0, "concluidos": 0})
                    atribuicoes_raw[a.user_id]["total"] += 1
                    if a.completed:
                        atribuicoes_raw[a.user_id]["concluidos"] += 1

            self.alunos = [
                {
                    "id": str(u.id),
                    "nome": u.nome_completo or u.nome_base or "",
                    "nome_base": u.nome_base or "",
                    "email": u.email,
                    "status": str(u.status),
                    "progresso": str(int(progressos_raw.get(u.id, 0))),
                    "estudos_total": str(atribuicoes_raw.get(u.id, {}).get("total", 0)),
                    "estudos_concluidos": str(atribuicoes_raw.get(u.id, {}).get("concluidos", 0)),
                    "selecionado": "false",
                }
                for u in alunos_list
            ]

            self.total_alunos = len(self.alunos)
            self.total_ativos = sum(
                1 for a in self.alunos if a.get("status") == "ativo"
            )

            # Média de progresso
            scores = list(progressos_raw.values())
            self.media_progresso = round(sum(scores) / len(scores), 1) if scores else 0.0

            # Pendências: atribuídos não concluídos
            self.pendencias = sum(
                info["total"] - info["concluidos"]
                for info in atribuicoes_raw.values()
            )

    def load_estudos(self):
        """Carrega estudos aprovados disponíveis para atribuição."""
        with rx.session() as session:
            estudos = session.exec(
                select(Study).where(
                    Study.status == StudyStatus.APROVADO,
                    Study.is_active == True,
                )
            ).all()
            self.estudos_disponiveis = [
                {
                    "id": str(e.id),
                    "titulo": e.title,
                    "nivel": str(e.level),
                    "descricao": e.description or "",
                }
                for e in estudos
            ]

    def load_turmas(self):
        """Carrega turmas sob responsabilidade do coordenador."""
        with rx.session() as session:
            turmas = session.exec(
                select(Turma).where(
                    Turma.coordenador_id == self.current_user_id,
                    Turma.is_active == True,
                )
            ).all()
            self.turmas = [
                {
                    "id": str(t.id),
                    "nome": t.nome,
                    "descricao": t.descricao or "",
                }
                for t in turmas
            ]

    # ── Seleção de alunos ────────────────────────────────────────

    def toggle_aluno(self, aluno_id: str):
        """Seleciona/deseleciona um aluno para atribuição de estudo."""
        try:
            aid = int(aluno_id)
        except (ValueError, TypeError):
            return
        if aid in self.selected_aluno_ids:
            self.selected_aluno_ids = [i for i in self.selected_aluno_ids if i != aid]
        else:
            self.selected_aluno_ids = self.selected_aluno_ids + [aid]

    def select_all_alunos(self):
        """Seleciona todos os alunos."""
        self.selected_aluno_ids = [
            int(a["id"]) for a in self.alunos if a.get("id")
        ]

    def clear_selection(self):
        """Limpa a seleção de alunos."""
        self.selected_aluno_ids = []
        self.message = ""

    # ── Atribuição de estudo ─────────────────────────────────────

    def assign_study(self):
        """Atribui o estudo selecionado aos alunos selecionados."""
        self.message = ""
        if not self.selected_study_option:
            self.message = "Selecione um estudo primeiro."
            self.message_type = "error"
            return
        if not self.selected_aluno_ids:
            self.message = "Selecione ao menos um aluno."
            self.message_type = "error"
            return

        try:
            study_id = int(self.selected_study_option.split(":")[0])
        except (ValueError, IndexError):
            self.message = "Estudo inválido."
            self.message_type = "error"
            return

        with rx.session() as session:
            version = StudyService.get_latest_version(study_id)
            if not version:
                self.message = "Estudo sem versão disponível."
                self.message_type = "error"
                return

            atribuidos = 0
            for aluno_id in self.selected_aluno_ids:
                existing = session.exec(
                    select(StudyAssignment).where(
                        StudyAssignment.user_id == aluno_id,
                        StudyAssignment.study_id == study_id,
                        StudyAssignment.study_version_id == version.id,
                    )
                ).first()
                if existing:
                    continue
                session.add(StudyAssignment(
                    user_id=aluno_id,
                    study_id=study_id,
                    study_version_id=version.id,
                    assigned_by=self.current_user_id,
                ))
                atribuidos += 1

            session.commit()

        if atribuidos == 0:
            self.message = "Todos os alunos já possuem este estudo."
            self.message_type = "info"
        else:
            self.message = f"Estudo atribuído a {atribuidos} aluno(s) com sucesso!"
            self.message_type = "success"

        self.selected_aluno_ids = []
        self.selected_study_option = ""
        self.load_alunos()
