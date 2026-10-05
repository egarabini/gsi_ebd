from datetime import datetime
from typing import List

from sqlmodel import select
import reflex as rx

from ..models.user import User, Role, UserStatus
from ..models.study import Study, StudyStatus
from ..models.notification import Notification, NotificationType
from ..models.lead import Lead, LeadStatus
from .auth import AuthState
from ..utils.rbac import can_manage
from ..services.user_status_service import UserStatusService


class AdminState(AuthState):
    # Criação de Gestor
    new_gestor_nome: str = ""
    new_gestor_email: str = ""
    new_gestor_password: str = ""

    # Listas carregadas (como dict para compatibilidade com foreach)
    gestores: list[dict] = []
    coordenadores: list[dict] = []
    leads: list[dict] = []
    estudos_pendentes: list[dict] = []

    # Controles de UI
    reject_motivo: str = ""
    message: str = ""
    message_type: str = "info"

    # ── Carregamento ────────────────────────────────────────────

    def load_gestores(self):
        with rx.session() as session:
            users = session.exec(
                select(User).where(User.role == Role.GESTOR)
            ).all()
            self.gestores = [
                {"id": u.id or 0, "nome": u.nome_completo, "email": u.email,
                 "status": u.status.value if hasattr(u.status, 'value') else str(u.status)}
                for u in users
            ]

    def load_coordenadores(self):
        with rx.session() as session:
            users = session.exec(
                select(User).where(User.role == Role.COORDENADOR)
            ).all()
            self.coordenadores = [
                {"id": u.id or 0, "nome": u.nome_completo, "email": u.email,
                 "status": u.status.value if hasattr(u.status, 'value') else str(u.status)}
                for u in users
            ]

    def load_leads(self):
        with rx.session() as session:
            leads = session.exec(
                select(Lead).order_by(Lead.created_at.desc())
            ).all()
            self.leads = [
                {"id": l.id or 0, "nome": l.nome, "email": l.email, "status": str(l.status)}
                for l in leads
            ]

    def load_estudos_pendentes(self):
        with rx.session() as session:
            estudos = session.exec(
                select(Study).where(
                    Study.status.in_([StudyStatus.PROPOSTO, StudyStatus.EM_REVISAO]),
                    Study.is_active == True,
                )
            ).all()
            self.estudos_pendentes = [
                {"id": e.id or 0, "titulo": e.title, "descricao": e.description or "",
                 "status": str(e.status), "proposto_por": e.proposto_por or 0}
                for e in estudos
            ]

    # ── Criação de Gestor (Admin cria; começa SUSPENSO) ─────────


    def create_gestor(self):
        if not self.is_admin:
            return rx.redirect("/login")
        import bcrypt
        with rx.session() as session:
            existing = session.exec(
                select(User).where(User.email == self.new_gestor_email)
            ).first()
            if existing:
                self.message = "Email já cadastrado"
                self.message_type = "error"
                return
            hashed = bcrypt.hashpw("senha123".encode(), bcrypt.gensalt()).decode()
            user = User(
                email=self.new_gestor_email,
                password_hash=hashed,
                nome_completo=self.new_gestor_nome,
                nome_base=self.new_gestor_nome.split()[0] if self.new_gestor_nome else "",
                role=Role.GESTOR,
                must_change_password=True,
                status=UserStatus.SUSPENSO,
                status_reason="Conta criada pelo Admin — aguardando confirmação por email",
            )
            session.add(user)
            session.flush()
            # Dispara email de confirmação
            UserStatusService.on_user_created(session, user)
            session.commit()
            self.message = f"Gestor '{user.nome_completo}' criado. Email de confirmação enviado para {user.email}."
            self.message_type = "success"
            self.new_gestor_nome = ""
            self.new_gestor_email = ""
            self.load_gestores()

    # ── Gestão de Status ──────────────────────────────────────────

    def activate_user(self, user_id: int):
        """Força ativação manual pelo Admin (sem precisar de email)."""
        with rx.session() as session:
            user = session.exec(select(User).where(User.id == user_id)).first()
            if user and can_manage(user.role, self.current_user_role):
                user.status = UserStatus.ATIVO
                user.status_reason = "Ativado manualmente pelo administrador"
                user.suspension_token = ""
                user.suspension_token_expires = None
                user.failed_login_attempts = 0
                session.add(user)
                session.commit()
        self._reload_all()

    def suspend_user(self, user_id: int):
        """Suspende manualmente um usuário. Admin nunca pode ser suspenso."""
        with rx.session() as session:
            user = session.exec(select(User).where(User.id == user_id)).first()
            if user and int(user.role) == Role.ADMIN:
                self.message = "O Administrador não pode ser suspenso."
                self.message_type = "error"
                return
            if user and can_manage(user.role, self.current_user_role):
                user.status = UserStatus.SUSPENSO
                user.status_reason = "Suspenso manualmente pelo administrador"
                session.add(user)
                session.commit()
        self._reload_all()

    def cancel_user(self, user_id: int):
        """Cancela definitivamente o acesso de um usuário."""
        with rx.session() as session:
            user = session.exec(select(User).where(User.id == user_id)).first()
            if user and can_manage(user.role, self.current_user_role):
                UserStatusService.cancel_user(
                    session, user,
                    reason="Cancelado pelo administrador",
                    cancelled_by=self.current_user_id or 0,
                )
                session.commit()
        self._reload_all()

    def _reload_all(self):
        self.load_gestores()
        self.load_coordenadores()

    # ── Leads ─────────────────────────────────────────────────────

    def update_lead_status(self, lead_id: int, new_status: str):
        with rx.session() as session:
            lead = session.exec(select(Lead).where(Lead.id == lead_id)).first()
            if lead:
                lead.status = new_status
                lead.updated_at = datetime.utcnow()
                session.add(lead)
                session.commit()
        self.load_leads()

    # ── Aprovação de Estudos ──────────────────────────────────────

    def aprovar_estudo(self, study_id: int):
        if not self.is_admin:
            return rx.redirect("/login")
        with rx.session() as session:
            study = session.exec(select(Study).where(Study.id == study_id)).first()
            if not study:
                return
            study.status = StudyStatus.APROVADO
            study.aprovado_por = self.current_user_id
            study.approved_at = datetime.utcnow()
            study.feedback_admin = ""
            session.add(study)
            if study.proposto_por:
                session.add(Notification(
                    user_id=study.proposto_por,
                    tipo=NotificationType.ESTUDO_APROVADO,
                    titulo="Estudo aprovado!",
                    mensagem=f"Seu estudo '{study.title}' foi aprovado e já pode ser atribuído.",
                    link="/gestor",
                ))
            session.commit()
        self.message = "Estudo aprovado com sucesso"
        self.message_type = "success"
        self.load_estudos_pendentes()

    def rejeitar_estudo(self, study_id: int):
        if not self.is_admin:
            return rx.redirect("/login")
        if not self.reject_motivo.strip():
            self.message = "Informe o motivo da rejeição"
            self.message_type = "error"
            return
        with rx.session() as session:
            study = session.exec(select(Study).where(Study.id == study_id)).first()
            if not study:
                return
            study.status = StudyStatus.REJEITADO
            study.aprovado_por = self.current_user_id
            study.feedback_admin = self.reject_motivo
            session.add(study)
            if study.proposto_por:
                session.add(Notification(
                    user_id=study.proposto_por,
                    tipo=NotificationType.ESTUDO_REJEITADO,
                    titulo="Estudo precisa de revisão",
                    mensagem=f"Seu estudo '{study.title}' foi rejeitado. Motivo: {self.reject_motivo}",
                    link="/gestor",
                ))
            session.commit()
        self.reject_motivo = ""
        self.message = "Estudo devolvido para revisão"
        self.message_type = "info"
        self.load_estudos_pendentes()
