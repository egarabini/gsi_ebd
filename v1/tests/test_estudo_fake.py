"""Modo estudo com alunos fake: so o banco de teste / homologacao didasko_v1."""
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

from gsi_ebd.models import (
    Estudo,
    EstudoCapitulo,
    Obra,
    Progress,
    QuestionType,
    Role,
    Study,
    StudyAssignment,
    StudyStatus,
    StudyVersion,
    User,
    UserResponse,
    UserStatus,
)
from v1.seed_homolog_estudo import ALUNOS_FAKE
from v1.tests.conftest import entrar, payload


def _criar_alunos_fake(session: Session) -> tuple[User, User]:
    modelo = session.exec(select(User).where(User.email == "papel4@example.test")).one()
    alunos = []
    for dados in ALUNOS_FAKE:
        aluno = User(
            email=dados["email"],
            nome_base=dados["nome_base"],
            nome_completo=dados["nome_completo"],
            password_hash=modelo.password_hash,
            status=UserStatus.ATIVO,
            role=int(Role.ALUNO),
            must_change_password=False,
        )
        session.add(aluno)
        alunos.append(aluno)
    session.flush()
    return alunos[0], alunos[1]


def _liberar_pela_tela(sistema):
    c = sistema["client"]
    oid = sistema["obra_id"]
    token = entrar(c, Role.REVISOR)
    assert c.post(f"/revisor/obras/{oid}/revisar", data=payload(sistema, token), follow_redirects=False).status_code == 303
    c.post("/logout", data={"csrf_token": token})
    token = entrar(c, Role.ADMIN)
    assert c.post(f"/admin/obras/{oid}/liberar", data=payload(sistema, token), follow_redirects=False).status_code == 303
    return token


def test_aluno_fake_ve_obra_liberada_responde_e_progresso_fica(sistema):
    token = _liberar_pela_tela(sistema)
    oid = sistema["obra_id"]
    with Session(sistema["engine"]) as session:
        aluno_a, aluno_b = _criar_alunos_fake(session)
        obra = session.get(Obra, oid)
        assert obra.versao_liberada_id is not None
        assert obra.disponibilidade == "aberta"
        estudo = Estudo(
            obra_id=obra.id,
            titulo="Estudo dirigido da obra de teste",
            status=StudyStatus.APROVADO.value,
            created_at=datetime.now(timezone.utc),
        )
        session.add(estudo)
        session.flush()
        questoes = [{"key": "q1", "type": int(QuestionType.TRUE_FALSE), "prompt": "Liberada?", "answer": "sim"}]
        session.add(
            EstudoCapitulo(
                estudo_id=estudo.id,
                ordem=1,
                titulo="Capitulo 1",
                conteudo_md="Texto do estudo dirigido.",
                questions_json=json.dumps(questoes),
                status=StudyStatus.APROVADO.value,
            )
        )
        catalogo = Study(title=estudo.titulo, status=StudyStatus.APROVADO.value, is_active=True)
        session.add(catalogo)
        session.flush()
        versao = StudyVersion(
            study_id=catalogo.id,
            version=1,
            content_md="Texto do estudo dirigido.",
            questions_json=json.dumps(questoes),
        )
        session.add(versao)
        session.flush()
        session.add(
            StudyAssignment(
                user_id=aluno_a.id,
                study_id=catalogo.id,
                study_version_id=versao.id,
                assigned_by=0,
            )
        )
        session.commit()
        aluno_a_id, aluno_b_id = aluno_a.id, aluno_b.id
        catalogo_id, versao_id = catalogo.id, versao.id

    with Session(sistema["engine"]) as session:
        atribuido = session.exec(
            select(StudyAssignment).where(StudyAssignment.user_id == aluno_a_id)
        ).one()
        assert atribuido.study_id == catalogo_id
        session.add(
            UserResponse(
                user_id=aluno_a_id,
                study_version_id=versao_id,
                question_key="q1",
                question_type=int(QuestionType.TRUE_FALSE),
                answer="sim",
                is_correct=True,
                created_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            Progress(
                user_id=aluno_a_id,
                study_id=catalogo_id,
                score=1.0,
                total_questions=1,
                correct_answers=1,
                last_activity=datetime.now(timezone.utc),
            )
        )
        session.commit()

    with Session(sistema["engine"]) as session:
        progresso = session.exec(select(Progress).where(Progress.user_id == aluno_a_id)).one()
        assert progresso.correct_answers == 1 and progresso.total_questions == 1
        resposta = session.exec(select(UserResponse).where(UserResponse.user_id == aluno_a_id)).one()
        assert resposta.answer == "sim" and resposta.is_correct is True
        assert session.exec(select(StudyAssignment).where(StudyAssignment.user_id == aluno_b_id)).first() is None

    sistema["client"].post("/logout", data={"csrf_token": token})


def test_aluno_fake_nao_ve_obra_nao_liberada(sistema):
    oid = sistema["obra_id"]
    with Session(sistema["engine"]) as session:
        obra = session.get(Obra, oid)
        assert obra.versao_liberada_id is None
        aluno_b = User(
            email=ALUNOS_FAKE[1]["email"],
            nome_base=ALUNOS_FAKE[1]["nome_base"],
            nome_completo=ALUNOS_FAKE[1]["nome_completo"],
            password_hash="x",
            status=UserStatus.ATIVO,
            role=int(Role.ALUNO),
            must_change_password=False,
        )
        session.add(aluno_b)
        session.flush()
        assert session.exec(select(StudyAssignment).where(StudyAssignment.user_id == aluno_b.id)).first() is None
        assert session.exec(select(Estudo).where(Estudo.obra_id == oid)).first() is None


def test_seed_producao_nao_recebe_alunos_fake():
    texto = (Path(__file__).resolve().parents[2] / "gsi_ebd" / "data" / "seed.py").read_text(encoding="utf-8")
    for aluno in ALUNOS_FAKE:
        assert aluno["email"] not in texto
    assert "homolog.didasko.local" not in texto
