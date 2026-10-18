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
from ..utils.rbac import exige


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
    # Obra (a fonte do estudo) e seus capítulos
    obras: list[dict] = []
    capitulos_obra: list[dict] = []
    # Estudo aplicável (capítulos próprios + origem)
    estudos_aplicados: list[dict] = []
    capitulos_estudo: list[dict] = []

    # Controles de UI
    reject_motivo: str = ""
    message: str = ""
    message_type: str = "info"
    # Aba ativa do painel. Fica no estado porque o menu lateral precisa poder
    # levar direto a uma aba — antes os itens do menu so apontavam para /admin
    # sem selecionar nada, e dois deles tinham o mesmo rotulo.
    tab_atual: str = "gestores"

    # ── Carregamento ────────────────────────────────────────────


    @exige("acao:usuarios")
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

    @exige("acao:leads")
    def load_leads(self):
        with rx.session() as session:
            leads = session.exec(
                select(Lead).order_by(Lead.created_at.desc())
            ).all()
            self.leads = [
                {"id": l.id or 0, "nome": l.nome, "email": l.email, "status": str(l.status)}
                for l in leads
            ]

    @exige("acao:catalogo_ler")
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

    @exige("acao:catalogo_ler")
    def load_obras(self):
        """Lista as obras (a fonte) e os capítulos da primeira.

        A obra não é o estudo que o aluno faz: é o material de origem. Os
        capítulos do estudo virão em outra fase e não correspondem
        necessariamente a estes.
        """
        from ..models import Obra, ObraCapitulo

        with rx.session() as session:
            obras = session.exec(select(Obra).order_by(Obra.titulo)).all()
            self.obras = []
            for obra in obras:
                capitulos = session.exec(
                    select(ObraCapitulo).where(ObraCapitulo.obra_id == obra.id)
                ).all()
                self.obras.append({
                    "id": str(obra.id),
                    "titulo": obra.titulo,
                    "tipo": obra.tipo,
                    # Concatenado AQUI, em Python: dentro do `rx.foreach` o valor
                    # é um Var, e `var + " texto"` estoura em tempo de compilação
                    # (TypeError: ObjectItemOperation + str). Aconteceu no deploy
                    # de 16/10 e derrubou o app em loop de restart.
                    "capitulos_label": f"{len(capitulos)} capítulos",
                })

            self.capitulos_obra = []
            if obras:
                for cap in session.exec(
                    select(ObraCapitulo)
                    .where(ObraCapitulo.obra_id == obras[0].id)
                    .order_by(ObraCapitulo.ordem)
                ).all():
                    self.capitulos_obra.append({
                        "ordem": f"{cap.ordem:02d}",
                        "titulo": cap.titulo,
                    })

    @exige("acao:catalogo_ler")
    def load_estudos_aplicados(self):
        """Lista o estudo aplicavel, seus capitulos e a origem de cada um.

        Os rotulos sao montados AQUI, em Python. Dentro do `rx.foreach` o valor e
        um Var, e `var + "texto"` estoura na compilacao da pagina — foi assim que
        o deploy de 16/10 derrubou o site em loop de restart.
        """
        from ..models import (
            Adendo,
            Estudo,
            EstudoCapitulo,
            EstudoCapituloOrigem,
            Obra,
            ObraCapitulo,
        )

        with rx.session() as session:
            estudos = session.exec(select(Estudo).order_by(Estudo.id)).all()

            resumo = []
            for estudo in estudos:
                capitulos = session.exec(
                    select(EstudoCapitulo)
                    .where(EstudoCapitulo.estudo_id == estudo.id)
                    .order_by(EstudoCapitulo.ordem)
                ).all()
                resumo.append((estudo, capitulos))

            self.estudos_aplicados = [{
                "titulo": estudo.titulo,
                "status": estudo.status,
                "capitulos_label": f"{len(capitulos)} capítulos",
            } for estudo, capitulos in resumo]

            self.capitulos_estudo = []
            if not resumo:
                return

            estudo, capitulos = resumo[0]
            obra = session.get(Obra, estudo.obra_id)
            titulo_obra = obra.titulo if obra is not None else "obra não encontrada"

            for cap in capitulos:
                origens = session.exec(
                    select(EstudoCapituloOrigem).where(
                        EstudoCapituloOrigem.estudo_capitulo_id == cap.id
                    )
                ).all()

                partes = []
                for origem in origens:
                    capitulo_obra = session.get(ObraCapitulo, origem.obra_capitulo_id)
                    if capitulo_obra is None:
                        continue
                    rotulo = f"{titulo_obra} · Cap. {capitulo_obra.ordem:02d}"
                    if origem.adendo_id:
                        adendo = session.get(Adendo, origem.adendo_id)
                        if adendo is not None:
                            rotulo += f" + {adendo.codigo}"
                    partes.append(rotulo)

                self.capitulos_estudo.append({
                    "ordem": f"{cap.ordem:02d}",
                    "titulo": cap.titulo,
                    "origem_label": " ; ".join(partes) if partes else "sem origem declarada",
                    "conteudo_label": f"{len(cap.conteudo_md):,}".replace(",", ".") + " caracteres",
                    "status": cap.status,
                })

    # ── Criação de Gestor (Admin cria; começa SUSPENSO) ─────────


    @exige("acao:usuarios")
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
                role=Role.COORDENADOR,
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
            self.load_coordenadores()

    # ── Gestão de Status ──────────────────────────────────────────

    @exige("acao:usuarios")
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

    @exige("acao:usuarios")
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

    @exige("acao:usuarios")
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
        self.load_coordenadores()
        self.load_coordenadores()

    # ── Leads ─────────────────────────────────────────────────────

    @exige("acao:leads")
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

    @exige("acao:catalogo_aprovar")
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
                    link="/coordenador",
                ))
            session.commit()
        self.message = "Estudo aprovado com sucesso"
        self.message_type = "success"
        self.load_estudos_pendentes()

    @exige("acao:catalogo_aprovar")
    def aprovar_todos(self):
        """Aprova de uma vez todos os estudos pendentes.

        Existe porque carga em massa entra como PROPOSTO (o importador traz 34
        capitulos) e exigiria 34 cliques. A validacao continua sendo uma decisao
        humana — so nao precisa ser repetida 34 vezes.
        """
        if not self.is_admin:
            return rx.redirect("/login")
        with rx.session() as session:
            pendentes = session.exec(
                select(Study).where(
                    Study.status.in_([StudyStatus.PROPOSTO, StudyStatus.EM_REVISAO]),
                    Study.is_active == True,
                )
            ).all()
            for estudo in pendentes:
                estudo.status = StudyStatus.APROVADO
                estudo.aprovado_por = self.current_user_id
                estudo.approved_at = datetime.utcnow()
                estudo.feedback_admin = ""
                session.add(estudo)
                if estudo.proposto_por:
                    session.add(Notification(
                        user_id=estudo.proposto_por,
                        tipo=NotificationType.ESTUDO_APROVADO,
                        titulo="Estudo aprovado!",
                        mensagem=f"Seu estudo '{estudo.title}' foi aprovado e já pode ser atribuído.",
                        link="/coordenador",
                    ))
            session.commit()
            quantos = len(pendentes)

        if quantos:
            self.message = f"{quantos} estudo(s) aprovado(s) e disponíveis para atribuição."
            self.message_type = "success"
        else:
            self.message = "Nenhum estudo pendente para aprovar."
            self.message_type = "info"
        self.load_estudos_pendentes()

    @exige("acao:catalogo_aprovar")
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
                    link="/coordenador",
                ))
            session.commit()
        self.reject_motivo = ""
        self.message = "Estudo devolvido para revisão"
        self.message_type = "info"
        self.load_estudos_pendentes()

    # ── Setters explicitos (state_auto_setters=False) ───────────────
    # So campo de formulario. Identidade (current_user_*) nao tem setter:
    # o cliente nao escreve o proprio papel.

    def set_tab_atual(self, v: str):
        self.tab_atual = v

    def set_new_gestor_nome(self, v: str):
        self.new_gestor_nome = v

    def set_new_gestor_email(self, v: str):
        self.new_gestor_email = v

    def set_reject_motivo(self, v: str):
        self.reject_motivo = v