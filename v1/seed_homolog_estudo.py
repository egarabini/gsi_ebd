"""Alunos fake do modo estudo. So o banco didasko_v1 de homologacao.

A producao nunca recebe este seed. O seed legado (gsi_ebd.data.seed) permanece
intocado.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import bcrypt
from sqlmodel import Session, select

from gsi_ebd.models import (
    Estudo,
    EstudoCapitulo,
    Obra,
    Role,
    Study,
    StudyAssignment,
    StudyStatus,
    StudyVersion,
    User,
    UserStatus,
)
from v1.db import assert_banco_v1, criar_engine, iniciar_banco

ALUNOS_FAKE = (
    {
        "email": "aluno.fake.a@homolog.didasko.local",
        "nome_base": "Aluno Fake A",
        "nome_completo": "Aluno Fake A (homologacao)",
    },
    {
        "email": "aluno.fake.b@homolog.didasko.local",
        "nome_base": "Aluno Fake B",
        "nome_completo": "Aluno Fake B (homologacao)",
    },
)


def recusar_producao(url: str | None = None, ambiente: str | None = None) -> str:
    """Recusa producao e qualquer banco que nao seja didasko_v1."""
    marcado = (ambiente if ambiente is not None else os.environ.get("DIDASKO_AMBIENTE", "")).strip().lower()
    if marcado == "producao":
        raise RuntimeError("seed de alunos fake recusado na producao")
    endereco = url if url is not None else os.environ.get("DATABASE_URL", "")
    if not endereco:
        raise RuntimeError("DATABASE_URL ausente")
    assert_banco_v1(endereco)
    return endereco


def _senha() -> str:
    senha = os.environ.get("SEED_PASSWORD", "")
    if not senha:
        raise RuntimeError("Defina SEED_PASSWORD para o seed de homologacao")
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()


def _aluno(session: Session, dados: dict, hash_senha: str) -> User:
    existente = session.exec(select(User).where(User.email == dados["email"])).first()
    if existente:
        return existente
    aluno = User(
        email=dados["email"],
        nome_base=dados["nome_base"],
        nome_completo=dados["nome_completo"],
        password_hash=hash_senha,
        status=UserStatus.ATIVO,
        role=int(Role.ALUNO),
        must_change_password=False,
    )
    session.add(aluno)
    session.flush()
    return aluno


def _estudo_da_obra_liberada(session: Session) -> tuple[Estudo, Study, StudyVersion] | None:
    obra = session.exec(select(Obra).where(Obra.versao_liberada_id.is_not(None))).first()
    if obra is None:
        return None
    estudo = session.exec(select(Estudo).where(Estudo.obra_id == obra.id)).first()
    if estudo is None:
        estudo = Estudo(
            obra_id=obra.id,
            titulo=f"Estudo de {obra.titulo}",
            descricao="Seed de homologacao — nao usar em producao",
            status=StudyStatus.APROVADO.value,
            created_at=datetime.now(timezone.utc),
        )
        session.add(estudo)
        session.flush()
        session.add(
            EstudoCapitulo(
                estudo_id=estudo.id,
                ordem=1,
                titulo="Capitulo 1",
                conteudo_md="Texto de estudo (homologacao).",
                questions_json='[{"key": "q1", "type": 2, "prompt": "A obra foi liberada?", "answer": "sim"}]',
                status=StudyStatus.APROVADO.value,
            )
        )
    catalogo = session.exec(select(Study).where(Study.title == estudo.titulo)).first()
    if catalogo is None:
        catalogo = Study(
            title=estudo.titulo,
            description=estudo.descricao,
            status=StudyStatus.APROVADO.value,
            is_active=True,
        )
        session.add(catalogo)
        session.flush()
        versao = StudyVersion(
            study_id=catalogo.id,
            version=1,
            content_md="Texto de estudo (homologacao).",
            questions_json='[{"key": "q1", "type": 2, "prompt": "A obra foi liberada?", "answer": "sim"}]',
        )
        session.add(versao)
        session.flush()
    else:
        versao = session.exec(
            select(StudyVersion).where(StudyVersion.study_id == catalogo.id).order_by(StudyVersion.version.desc())
        ).first()
    return estudo, catalogo, versao


def popular(session: Session) -> None:
    hash_senha = _senha()
    aluno_a = _aluno(session, ALUNOS_FAKE[0], hash_senha)
    _aluno(session, ALUNOS_FAKE[1], hash_senha)
    artefatos = _estudo_da_obra_liberada(session)
    if artefatos is None:
        return
    _, catalogo, versao = artefatos
    ja = session.exec(
        select(StudyAssignment).where(
            StudyAssignment.user_id == aluno_a.id,
            StudyAssignment.study_id == catalogo.id,
        )
    ).first()
    if ja is None:
        session.add(
            StudyAssignment(
                user_id=aluno_a.id,
                study_id=catalogo.id,
                study_version_id=versao.id,
                assigned_by=0,
            )
        )


def run() -> None:
    url = recusar_producao()
    engine = criar_engine(url)
    iniciar_banco(engine)
    with Session(engine) as session:
        popular(session)
        session.commit()


if __name__ == "__main__":
    run()
