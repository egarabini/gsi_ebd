"""Avaliacao humana das respostas abertas — o ciclo do INSTRUTOR.

Inspirado no modelo que originou o GSI-EBD (SGI7 / "Siga a Biblia"), onde o
instrutor recebe as respostas do aluno, corrige e devolve um parecer. Aqui as
questoes abertas nascem com is_correct=None e permanecem na fila ate alguem
avaliar.
"""
from datetime import datetime
from typing import Dict, List, Optional

import reflex as rx
from sqlmodel import or_, select

from ..models import (
    Ambiente, Progress, Role, Study, StudyAssignment, StudyVersion, Turma, TurmaMembro,
    User, UserResponse, UserStatus,
)


class ReviewService:
    # ── Escopo: quem este instrutor pode avaliar ────────────────────────────
    @staticmethod
    def _alunos_do_avaliador(user_id: int, role: int) -> List[int]:
        """Ids dos alunos que este avaliador pode corrigir.

        Hierarquia: ADMIN > COORDENADOR > INSTRUTOR > ALUNO.
        - INSTRUTOR  : apenas os SEUS alunos (instrutor_id) e membros das suas turmas.
        - COORDENADOR: todos os alunos do seu ambiente (visao de supervisao).
        - ADMIN      : todos.
        """
        with rx.session() as session:
            if role == Role.ADMIN:
                return [u.id for u in session.exec(
                    select(User).where(User.role == Role.ALUNO)).all()]

            if role == Role.COORDENADOR:
                diretos = [u.id for u in session.exec(
                    select(User).where(User.role == Role.ALUNO,
                                       User.coordenador_id == user_id)).all()]
                via_ambiente = [u.id for u in session.exec(
                    select(User).where(User.role == Role.ALUNO,
                                       User.ambiente_id.in_(
                                           select(Ambiente.id).where(
                                               Ambiente.coordenador_id == user_id)))).all()]
                via_turma = ReviewService._alunos_das_turmas(user_id, session)
                return sorted(set(diretos + via_ambiente + via_turma))

            # INSTRUTOR (e qualquer outro): apenas os seus alunos
            diretos = [u.id for u in session.exec(
                select(User).where(User.role == Role.ALUNO,
                                   User.instrutor_id == user_id)).all()]
            via_turma = ReviewService._alunos_das_turmas(user_id, session)
            return sorted(set(diretos + via_turma))

    @staticmethod
    def _alunos_das_turmas(user_id: int, session) -> List[int]:
        """Alunos das turmas conduzidas por este usuario (como instrutor)."""
        turma_ids = [t.id for t in session.exec(
            select(Turma).where(or_(Turma.instrutor_id == user_id,
                                    Turma.coordenador_id == user_id),
                                Turma.is_active == True)).all()]
        if not turma_ids:
            return []
        membros = session.exec(
            select(TurmaMembro).where(TurmaMembro.turma_id.in_(turma_ids),
                                      TurmaMembro.is_active == True)).all()
        return [m.user_id for m in membros]

    # ── Fila de correcao ────────────────────────────────────────────────────
    @staticmethod
    def fila_pendente(user_id: int, role: int) -> List[Dict]:
        """Respostas abertas aguardando parecer, agrupadas por aluno e licao."""
        aluno_ids = ReviewService._alunos_do_avaliador(user_id, role)
        if not aluno_ids:
            return []
        with rx.session() as session:
            respostas = session.exec(
                select(UserResponse)
                .where(UserResponse.user_id.in_(aluno_ids),
                       UserResponse.is_correct == None,          # noqa: E711
                       UserResponse.instructor_feedback == "")
                .order_by(UserResponse.created_at)
            ).all()
            if not respostas:
                return []

            alunos = {u.id: u for u in session.exec(
                select(User).where(User.id.in_(aluno_ids))).all()}
            versoes = {v.id: v for v in session.exec(
                select(StudyVersion).where(
                    StudyVersion.id.in_({r.study_version_id for r in respostas}))).all()}
            estudos = {s.id: s for s in session.exec(
                select(Study).where(
                    Study.id.in_({v.study_id for v in versoes.values()}))).all()}

            itens: List[Dict] = []
            for r in respostas:
                versao = versoes.get(r.study_version_id)
                estudo = estudos.get(versao.study_id) if versao else None
                aluno = alunos.get(r.user_id)
                itens.append({
                    "response_id": str(r.id),
                    "aluno_nome": aluno.nome_completo if aluno else "?",
                    "estudo_titulo": estudo.title if estudo else "?",
                    "pergunta_chave": r.question_key,
                    "resposta": r.answer or "",
                    "quando": r.created_at.strftime("%d/%m/%Y %H:%M") if r.created_at else "",
                })
            return itens

    # ── Registrar parecer ───────────────────────────────────────────────────
    @staticmethod
    def registrar_parecer(response_id: int, instrutor_id: int, role: int,
                          parecer: str, considerou_correto: Optional[bool]) -> str:
        with rx.session() as session:
            r = session.exec(select(UserResponse).where(
                UserResponse.id == response_id)).first()
            if not r:
                return "Resposta nao encontrada"
            permitidos = ReviewService._alunos_do_avaliador(instrutor_id, role)
            if r.user_id not in permitidos:
                return "Voce nao acompanha este aluno"
            if not parecer.strip():
                return "Escreva um parecer antes de salvar"
            r.instructor_feedback = parecer.strip()
            r.is_correct = considerou_correto
            r.reviewed_by = instrutor_id
            r.reviewed_at = datetime.utcnow()
            session.add(r)
            session.commit()
            # A nota do aluno precisa refletir a avaliacao recem-feita.
            ReviewService._recalcular_nota(session, r.user_id, r.study_version_id)
            return ""

    @staticmethod
    def _recalcular_nota(session, aluno_id: int, versao_id: int) -> None:
        """Recalcula Progress do aluno somando as questoes ja avaliadas.

        Antes da correcao, as abertas ficavam fora da conta (is_correct=None).
        Quando o instrutor avalia, elas passam a contar — este metodo refaz a
        conta para o aluno ver a nota atualizada.
        """
        respostas = session.exec(
            select(UserResponse).where(UserResponse.user_id == aluno_id,
                                       UserResponse.study_version_id == versao_id)).all()
        avaliadas = [r for r in respostas if r.is_correct is not None]
        if not avaliadas:
            return
        acertos = sum(1 for r in avaliadas if r.is_correct)
        novo_score = round(acertos / len(avaliadas) * 100, 2)

        versao = session.exec(select(StudyVersion).where(
            StudyVersion.id == versao_id)).first()
        if not versao:
            return
        progresso = session.exec(
            select(Progress).where(Progress.user_id == aluno_id,
                                   Progress.study_id == versao.study_id)).first()
        if progresso:
            progresso.score = novo_score
            progresso.total_questions = len(avaliadas)
            progresso.correct_answers = acertos
            progresso.last_activity = datetime.utcnow()
            session.add(progresso)
            session.commit()

    # ── Visao do aluno ──────────────────────────────────────────────────────
    @staticmethod
    def pareceres_do_aluno(aluno_id: int) -> List[Dict]:
        with rx.session() as session:
            respostas = session.exec(
                select(UserResponse)
                .where(UserResponse.user_id == aluno_id,
                       UserResponse.instructor_feedback != "")
                .order_by(UserResponse.reviewed_at.desc())
            ).all()
            if not respostas:
                return []
            versoes = {v.id: v for v in session.exec(
                select(StudyVersion).where(
                    StudyVersion.id.in_({r.study_version_id for r in respostas}))).all()}
            estudos = {s.id: s for s in session.exec(
                select(Study).where(
                    Study.id.in_({v.study_id for v in versoes.values()}))).all()}
            instrutores = {u.id: u for u in session.exec(
                select(User).where(User.id.in_({r.reviewed_by for r in respostas
                                                if r.reviewed_by}))).all()}
            out = []
            for r in respostas:
                versao = versoes.get(r.study_version_id)
                estudo = estudos.get(versao.study_id) if versao else None
                instr = instrutores.get(r.reviewed_by)
                out.append({
                    "estudo_titulo": estudo.title if estudo else "?",
                    "pergunta_chave": r.question_key,
                    "resposta": r.answer or "",
                    "parecer": r.instructor_feedback,
                    "instrutor": instr.nome_completo if instr else "Instrutor",
                    "quando": r.reviewed_at.strftime("%d/%m/%Y") if r.reviewed_at else "",
                    "correto": "sim" if r.is_correct else "revisar",
                })
            return out

    # ── Contadores para o painel ────────────────────────────────────────────
    @staticmethod
    def total_pendente(user_id: int, role: int) -> int:
        return len(ReviewService.fila_pendente(user_id, role))
