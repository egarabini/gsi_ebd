"""Modo estudo com alunos fake: login real, GET/POST e so o banco didasko_v1."""
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
from v1.tests.conftest import entrar, entrar_como, payload


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


def _montar_estudo(session: Session, obra: Obra, aluno: User) -> tuple[int, int]:
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
            user_id=aluno.id,
            study_id=catalogo.id,
            study_version_id=versao.id,
            assigned_by=0,
        )
    )
    return catalogo.id, versao.id


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
        catalogo_id, _versao_id = _montar_estudo(session, obra, aluno_a)
        session.commit()
        aluno_a_id, aluno_b_id = aluno_a.id, aluno_b.id

    sistema["client"].post("/logout", data={"csrf_token": token})
    c = sistema["client"]
    token = entrar_como(c, ALUNOS_FAKE[0]["email"])
    casa = c.get("/aluno", follow_redirects=False)
    assert casa.status_code == 200, casa.text
    assert "Estudo dirigido da obra de teste" in casa.text
    licao = c.get(f"/aluno/licao/{catalogo_id}", follow_redirects=False)
    assert licao.status_code == 200, licao.text
    assert "Liberada?" in licao.text
    resposta = c.post(
        f"/aluno/licao/{catalogo_id}",
        data={"csrf_token": token, "question_key": "q1", "answer": "sim"},
        follow_redirects=False,
    )
    assert resposta.status_code == 303, resposta.text

    with Session(sistema["engine"]) as session:
        progresso = session.exec(select(Progress).where(Progress.user_id == aluno_a_id)).one()
        assert progresso.correct_answers == 1 and progresso.total_questions == 1
        gravada = session.exec(select(UserResponse).where(UserResponse.user_id == aluno_a_id)).one()
        assert gravada.answer == "sim" and gravada.is_correct is True
        assert session.exec(select(StudyAssignment).where(StudyAssignment.user_id == aluno_b_id)).first() is None

    c.post("/logout", data={"csrf_token": token})


def test_aluno_fake_nao_ve_obra_nao_liberada(sistema):
    oid = sistema["obra_id"]
    with Session(sistema["engine"]) as session:
        obra = session.get(Obra, oid)
        assert obra.versao_liberada_id is None
        _aluno_a, aluno_b = _criar_alunos_fake(session)
        catalogo_id, _versao_id = _montar_estudo(session, obra, aluno_b)
        session.commit()

    c = sistema["client"]
    token = entrar_como(c, ALUNOS_FAKE[1]["email"])
    casa = c.get("/aluno", follow_redirects=False)
    assert casa.status_code == 200, casa.text
    assert "Estudo dirigido da obra de teste" not in casa.text
    assert "Nenhum estudo liberado" in casa.text
    licao = c.get(f"/aluno/licao/{catalogo_id}", follow_redirects=False)
    assert licao.status_code == 403
    assert c.get(f"/obras/{oid}", follow_redirects=False).status_code == 403
    c.post("/logout", data={"csrf_token": token})


def test_seed_producao_nao_recebe_alunos_fake():
    texto = (Path(__file__).resolve().parents[2] / "gsi_ebd" / "data" / "seed.py").read_text(encoding="utf-8")
    for aluno in ALUNOS_FAKE:
        assert aluno["email"] not in texto
    assert "homolog.didasko.local" not in texto
