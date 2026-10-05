"""
GestorState — gerencia o painel completo do Gestor.

Hierarquia gerenciada pelo Gestor:
  Gestor → Supervisores → Alunos

O Gestor pode:
  - Criar/listar seus Supervisores
  - Criar/listar seus Alunos (diretos ou via supervisores)
  - Propor estudos ao Admin
  - Ver estudos aprovados e atribuí-los
  - Ver progresso geral da equipe
"""
import bcrypt
from datetime import datetime
from typing import List

from sqlmodel import select
import reflex as rx

from ..models.user import User, Role, UserStatus
from ..models.study import Study, StudyVersion, StudyAssignment, StudyStatus, StudyLevel
from ..models.notification import Notification, NotificationType
from ..services.study_service import StudyService
from ..services.user_status_service import UserStatusService
from .auth import AuthState

DEFAULT_PASSWORD = "senha123"


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


class GestorState(AuthState):
    # ── Formulários de criação ────────────────────────────────────
    new_supervisor_nome: str = ""
    new_supervisor_email: str = ""

    new_aluno_nome: str = ""
    new_aluno_email: str = ""

    new_study_title: str = ""
    new_study_description: str = ""
    new_study_category: str = "geral"
    new_study_level: str = StudyLevel.BASICO
    new_study_content_md: str = ""

    # ── Listas (list[dict] para rx.foreach) ──────────────────────
    supervisores: list[dict] = []
    alunos: list[dict] = []
    estudos_aprovados: list[dict] = []
    estudos_propostos: list[dict] = []

    # ── Atribuição de estudos ────────────────────────────────────
    selected_study_id: str = ""
    selected_aluno_ids: list[int] = []

    # ── Métricas ─────────────────────────────────────────────────
    total_supervisores: int = 0
    total_alunos: int = 0
    total_estudos_ativos: int = 0
    total_pendentes: int = 0

    # ── Feedback ─────────────────────────────────────────────────
    message: str = ""
    message_type: str = "info"

    # ── Opções de nível para select ──────────────────────────────
    study_levels: list[str] = [
        StudyLevel.BASICO,
        StudyLevel.MEDIO,
        StudyLevel.AVANCADO,
        StudyLevel.MASTER,
    ]

    # ── Computed vars ────────────────────────────────────────────
    @rx.var
    def study_options(self) -> list[str]:
        opts = []
        for e in self.estudos_aprovados:
            try:
                eid = e.get("id", "") if hasattr(e, "get") else e["id"]
                etit = e.get("titulo", "") if hasattr(e, "get") else e["titulo"]
                opts.append(f"{eid}:{etit}")
            except Exception:
                pass
        return opts

    @rx.var
    def has_supervisores(self) -> bool:
        return self.total_supervisores > 0

    @rx.var
    def has_alunos(self) -> bool:
        return self.total_alunos > 0

    @rx.var
    def has_estudos_aprovados(self) -> bool:
        return self.total_estudos_ativos > 0

    # ── Carregamento ─────────────────────────────────────────────

    def load_all(self):
        """Carrega todos os dados do gestor de uma vez."""
        self.load_supervisores()
        self.load_alunos()
        self.load_estudos_aprovados()
        self.load_estudos_propostos()

    def load_supervisores(self):
        """Carrega supervisores vinculados a este gestor."""
        with rx.session() as session:
            users = session.exec(
                select(User).where(
                    User.role == Role.SUPERVISOR,
                    User.gestor_id == self.current_user_id,
                )
            ).all()
            self.supervisores = [
                {
                    "id": str(u.id),
                    "nome": u.nome_completo or u.nome_base or "",
                    "nome_base": u.nome_base or (u.nome_completo or "?")[0],
                    "email": u.email,
                    "status": str(u.status),
                }
                for u in users
            ]
            self.total_supervisores = len(self.supervisores)

    def load_alunos(self):
        """
        Carrega alunos do gestor.
        Inclui alunos diretos (gestor_id) e alunos dos supervisores do gestor.
        """
        with rx.session() as session:
            # Alunos diretos do gestor
            alunos_diretos = session.exec(
                select(User).where(
                    User.role == Role.ALUNO,
                    User.gestor_id == self.current_user_id,
                )
            ).all()

            # IDs dos supervisores deste gestor
            sup_ids = [u.id for u in session.exec(
                select(User).where(
                    User.role == Role.SUPERVISOR,
                    User.gestor_id == self.current_user_id,
                )
            ).all()]

            # Alunos vinculados a esses supervisores
            alunos_via_sup = []
            if sup_ids:
                alunos_via_sup = session.exec(
                    select(User).where(
                        User.role == Role.ALUNO,
                        User.supervisor_id.in_(sup_ids),
                    )
                ).all()

            # Unifica sem duplicatas
            todos = {u.id: u for u in alunos_diretos + alunos_via_sup}
            alunos_list = list(todos.values())

            self.alunos = [
                {
                    "id": str(u.id),
                    "nome": u.nome_completo or u.nome_base or "",
                    "nome_base": u.nome_base or (u.nome_completo or "?")[0],
                    "email": u.email,
                    "status": str(u.status),
                    "supervisor_id": str(u.supervisor_id or ""),
                }
                for u in alunos_list
            ]
            self.total_alunos = len(self.alunos)

    def load_estudos_aprovados(self):
        """Carrega estudos aprovados disponíveis para atribuição."""
        with rx.session() as session:
            estudos = session.exec(
                select(Study).where(
                    Study.status == StudyStatus.APROVADO,
                    Study.is_active == True,
                )
            ).all()
            self.estudos_aprovados = [
                {
                    "id": str(e.id),
                    "titulo": e.title,
                    "nivel": str(e.level),
                    "descricao": e.description or "",
                }
                for e in estudos
            ]
            self.total_estudos_ativos = len(self.estudos_aprovados)

    def load_estudos_propostos(self):
        """Carrega estudos propostos por este gestor."""
        with rx.session() as session:
            estudos = session.exec(
                select(Study).where(Study.proposto_por == self.current_user_id)
            ).all()
            self.estudos_propostos = [
                {
                    "id": str(e.id),
                    "titulo": e.title,
                    "descricao": e.description or "",
                    "status": str(e.status),
                    "nivel": str(e.level),
                }
                for e in estudos
            ]
            self.total_pendentes = sum(
                1 for e in self.estudos_propostos
                if e.get("status") in ("StudyStatus.PROPOSTO", "proposto", "em_revisao", "StudyStatus.EM_REVISAO")
            )

    # ── Criação de Supervisor ────────────────────────────────────

    def create_supervisor(self):
        """Cria um novo Supervisor vinculado a este Gestor."""
        self.message = ""
        if not self.new_supervisor_nome.strip() or not self.new_supervisor_email.strip():
            self.message = "Preencha nome e email do supervisor."
            self.message_type = "error"
            return

        with rx.session() as session:
            if session.exec(
                select(User).where(User.email == self.new_supervisor_email)
            ).first():
                self.message = "Email já cadastrado na plataforma."
                self.message_type = "error"
                return

            user = User(
                email=self.new_supervisor_email,
                password_hash=_hash(DEFAULT_PASSWORD),
                nome_completo=self.new_supervisor_nome,
                nome_base=self.new_supervisor_nome.split()[0] if self.new_supervisor_nome else "",
                role=Role.SUPERVISOR,
                gestor_id=self.current_user_id,
                must_change_password=True,
                status=UserStatus.SUSPENSO,
                status_reason="Conta criada pelo Gestor — aguardando confirmação por email",
                assinatura_ativa=True,
            )
            session.add(user)
            session.flush()
            UserStatusService.on_user_created(session, user)
            session.commit()

        self.message = f"Supervisor '{self.new_supervisor_nome}' criado! Email de confirmação enviado."
        self.message_type = "success"
        self.new_supervisor_nome = ""
        self.new_supervisor_email = ""
        self.load_supervisores()

    def activate_supervisor(self, sup_id: str):
        """Ativa um supervisor manualmente."""
        with rx.session() as session:
            user = session.exec(select(User).where(User.id == int(sup_id))).first()
            if user and str(user.gestor_id) == str(self.current_user_id):
                user.status = UserStatus.ATIVO
                user.status_reason = "Ativado pelo Gestor"
                user.suspension_token = ""
                user.suspension_token_expires = None
                user.failed_login_attempts = 0
                session.add(user)
                session.commit()
        self.load_supervisores()

    # ── Criação de Aluno ─────────────────────────────────────────

    def create_aluno(self):
        """Cria um novo Aluno vinculado diretamente a este Gestor."""
        self.message = ""
        if not self.new_aluno_nome.strip() or not self.new_aluno_email.strip():
            self.message = "Preencha nome e email do aluno."
            self.message_type = "error"
            return

        with rx.session() as session:
            if session.exec(
                select(User).where(User.email == self.new_aluno_email)
            ).first():
                self.message = "Email já cadastrado na plataforma."
                self.message_type = "error"
                return

            user = User(
                email=self.new_aluno_email,
                password_hash=_hash(DEFAULT_PASSWORD),
                nome_completo=self.new_aluno_nome,
                nome_base=self.new_aluno_nome.split()[0] if self.new_aluno_nome else "",
                role=Role.ALUNO,
                gestor_id=self.current_user_id,
                must_change_password=True,
                status=UserStatus.SUSPENSO,
                status_reason="Conta criada pelo Gestor — aguardando confirmação por email",
                assinatura_ativa=True,
            )
            session.add(user)
            session.flush()
            UserStatusService.on_user_created(session, user)
            session.commit()

        self.message = f"Aluno '{self.new_aluno_nome}' criado! Email de confirmação enviado."
        self.message_type = "success"
        self.new_aluno_nome = ""
        self.new_aluno_email = ""
        self.load_alunos()

    def activate_aluno(self, aluno_id: str):
        """Ativa um aluno manualmente."""
        with rx.session() as session:
            user = session.exec(select(User).where(User.id == int(aluno_id))).first()
            if user:
                user.status = UserStatus.ATIVO
                user.status_reason = "Ativado pelo Gestor"
                user.suspension_token = ""
                user.suspension_token_expires = None
                user.failed_login_attempts = 0
                session.add(user)
                session.commit()
        self.load_alunos()

    # ── Seleção de alunos para atribuição ───────────────────────

    def toggle_aluno(self, aluno_id: str):
        try:
            aid = int(aluno_id)
        except (ValueError, TypeError):
            return
        if aid in self.selected_aluno_ids:
            self.selected_aluno_ids = [i for i in self.selected_aluno_ids if i != aid]
        else:
            self.selected_aluno_ids = self.selected_aluno_ids + [aid]

    def select_all_alunos(self):
        self.selected_aluno_ids = [int(a["id"]) for a in self.alunos if a.get("id")]

    def clear_selection(self):
        self.selected_aluno_ids = []

    # ── Atribuição de estudos ────────────────────────────────────

    def assign_study(self):
        self.message = ""
        if not self.selected_study_id or not self.selected_aluno_ids:
            self.message = "Selecione um estudo e ao menos um aluno."
            self.message_type = "error"
            return

        try:
            study_id = int(self.selected_study_id.split(":")[0])
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
            self.message = f"Estudo atribuído a {atribuidos} aluno(s)!"
            self.message_type = "success"

        self.selected_aluno_ids = []
        self.selected_study_id = ""

    # ── Proposta de estudos ──────────────────────────────────────

    def propor_estudo(self):
        self.message = ""
        if not self.new_study_title.strip() or not self.new_study_content_md.strip():
            self.message = "Informe título e conteúdo do estudo."
            self.message_type = "error"
            return

        with rx.session() as session:
            study = Study(
                title=self.new_study_title,
                description=self.new_study_description,
                category=self.new_study_category or "geral",
                level=self.new_study_level,
                status=StudyStatus.PROPOSTO,
                proposto_por=self.current_user_id,
                is_active=True,
            )
            session.add(study)
            session.flush()
            session.add(StudyVersion(
                study_id=study.id,
                version=1,
                content_md=self.new_study_content_md,
                questions_json="[]",
            ))
            # Notifica admins
            admins = session.exec(select(User).where(User.role == Role.ADMIN)).all()
            for admin in admins:
                session.add(Notification(
                    user_id=admin.id,
                    tipo=NotificationType.ESTUDO_PROPOSTO,
                    titulo="Novo estudo proposto",
                    mensagem=f"O estudo '{study.title}' foi proposto e aguarda avaliação.",
                    link="/admin",
                ))
            session.commit()

        self.message = "Estudo enviado para avaliação do Admin!"
        self.message_type = "success"
        self.new_study_title = ""
        self.new_study_description = ""
        self.new_study_category = "geral"
        self.new_study_level = StudyLevel.BASICO
        self.new_study_content_md = ""
        self.load_estudos_propostos()
