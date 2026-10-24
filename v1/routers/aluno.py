"""Fluxo minimo do aluno: ver o estudo da obra liberada e registrar a resposta.

Telas completas do aluno ficam para outra fatia. Aqui so o caminho HTTP que o
plano de testes §3 exige (GET 200, POST 303, progresso no banco).
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from gsi_ebd.models import (
    Estudo,
    Obra,
    Progress,
    QuestionType,
    Study,
    StudyAssignment,
    StudyVersion,
    User,
    UserResponse,
)
from v1.auth import exigir, verificar_csrf, verificar_h14
from v1.db import sessao
from v1.views import render

router = APIRouter(dependencies=[Depends(verificar_csrf), Depends(verificar_h14)])
CASA = exigir("rota:/aluno")
LICAO = exigir("rota:/aluno/licao")
TIPOS = {
    "fill_blank": int(QuestionType.FILL_BLANK),
    "true_false": int(QuestionType.TRUE_FALSE),
    "multiple_choice": int(QuestionType.MULTIPLE_CHOICE),
    "open": int(QuestionType.OPEN),
}


def _obra_liberada(session: Session, study: Study) -> Obra | None:
    aplicavel = session.exec(select(Estudo).where(Estudo.titulo == study.title)).first()
    if aplicavel is None:
        return None
    obra = session.get(Obra, aplicavel.obra_id)
    if obra is None or obra.versao_liberada_id is None:
        return None
    if obra.disponibilidade != "aberta":
        return None
    return obra


def _atribuicao_liberada(session: Session, usuario: User, study_id: int) -> StudyAssignment | None:
    atribuicao = session.exec(
        select(StudyAssignment).where(
            StudyAssignment.user_id == usuario.id,
            StudyAssignment.study_id == study_id,
        )
    ).first()
    if atribuicao is None:
        return None
    estudo = session.get(Study, study_id)
    if estudo is None or _obra_liberada(session, estudo) is None:
        return None
    return atribuicao


def _estudos_do_aluno(session: Session, usuario: User) -> list[Study]:
    atribuicoes = session.exec(
        select(StudyAssignment).where(StudyAssignment.user_id == usuario.id)
    ).all()
    visiveis = []
    for atribuicao in atribuicoes:
        estudo = session.get(Study, atribuicao.study_id)
        if estudo is not None and _obra_liberada(session, estudo) is not None:
            visiveis.append(estudo)
    return visiveis


def _questoes(versao: StudyVersion) -> list[dict]:
    try:
        dados = json.loads(versao.questions_json or "[]")
    except json.JSONDecodeError:
        return []
    return dados if isinstance(dados, list) else []


def _tipo(questao: dict) -> int:
    bruto = questao.get("type", int(QuestionType.TRUE_FALSE))
    if isinstance(bruto, str):
        return TIPOS.get(bruto.strip().lower(), int(QuestionType.TRUE_FALSE))
    try:
        return int(bruto)
    except (TypeError, ValueError):
        return int(QuestionType.TRUE_FALSE)


@router.get("/aluno")
def lista(request: Request, session: Session = Depends(sessao), usuario: User = Depends(CASA)):
    return render(
        request,
        "aluno/lista.html",
        {"titulo": "Meus estudos", "estudos": _estudos_do_aluno(session, usuario)},
    )


@router.get("/aluno/licao/{study_id}")
def licao(
    request: Request,
    study_id: int,
    session: Session = Depends(sessao),
    usuario: User = Depends(LICAO),
):
    atribuicao = _atribuicao_liberada(session, usuario, study_id)
    if atribuicao is None:
        raise HTTPException(403, "Estudo indisponivel para este aluno.")
    estudo = session.get(Study, study_id)
    versao = session.get(StudyVersion, atribuicao.study_version_id)
    if estudo is None or versao is None:
        raise HTTPException(404, "Estudo nao encontrado")
    return render(
        request,
        "aluno/licao.html",
        {
            "titulo": estudo.title,
            "estudo": estudo,
            "versao": versao,
            "questoes": _questoes(versao),
        },
    )


@router.post("/aluno/licao/{study_id}")
def responder(
    request: Request,
    study_id: int,
    question_key: str = Form(""),
    answer: str = Form(""),
    session: Session = Depends(sessao),
    usuario: User = Depends(LICAO),
):
    atribuicao = _atribuicao_liberada(session, usuario, study_id)
    if atribuicao is None:
        raise HTTPException(403, "Estudo indisponivel para este aluno.")
    versao = session.get(StudyVersion, atribuicao.study_version_id)
    if versao is None:
        raise HTTPException(404, "Estudo nao encontrado")
    chave = question_key.strip()
    questao = next((item for item in _questoes(versao) if str(item.get("key", "")) == chave), None)
    if questao is None:
        raise HTTPException(404, "Questao nao encontrada")
    esperada = str(questao.get("answer", ""))
    acertou = answer.strip().lower() == esperada.strip().lower()
    agora = datetime.now(timezone.utc)
    session.add(
        UserResponse(
            user_id=usuario.id,
            study_version_id=versao.id,
            question_key=chave,
            question_type=_tipo(questao),
            answer=answer,
            is_correct=acertou,
            created_at=agora,
        )
    )
    progresso = session.exec(
        select(Progress).where(Progress.user_id == usuario.id, Progress.study_id == study_id)
    ).first()
    if progresso is None:
        progresso = Progress(
            user_id=usuario.id,
            study_id=study_id,
            total_questions=0,
            correct_answers=0,
            score=0.0,
        )
        session.add(progresso)
    progresso.total_questions += 1
    progresso.correct_answers += int(acertou)
    if progresso.total_questions:
        progresso.score = progresso.correct_answers / progresso.total_questions
    progresso.last_activity = agora
    session.commit()
    return RedirectResponse(f"/aluno/licao/{study_id}", status_code=303)
