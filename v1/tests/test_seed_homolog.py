"""O seed de alunos fake recusa producao e qualquer banco que nao seja didasko_v1."""
from pathlib import Path

import bcrypt
import pytest
from sqlmodel import Session, select

from gsi_ebd.models import Adendo, Estudo, Obra, ObraCapitulo, Role, Study, StudyAssignment, User, UserStatus
from gsi_ebd.services import flow, fontes
from v1.db import assert_banco_v1, criar_engine, iniciar_banco
from v1.seed_homolog_estudo import ALUNOS_FAKE, popular, recusar_producao, run


def test_seed_homolog_recusa_producao():
    with pytest.raises(RuntimeError, match="producao"):
        recusar_producao(
            url="postgresql+psycopg2://didasko_v1:segredo@postgres:5432/didasko_v1",
            ambiente="producao",
        )


def test_seed_homolog_recusa_banco_que_nao_e_didasko_v1():
    with pytest.raises(RuntimeError):
        recusar_producao(
            url="postgresql+psycopg2://didasko:segredo@postgres:5432/didasko",
            ambiente="homologacao",
        )
    with pytest.raises(RuntimeError):
        assert_banco_v1("postgresql+psycopg2://didasko:segredo@postgres:5432/didasko")


def test_seed_homolog_aceita_didasko_v1_de_homologacao():
    url = recusar_producao(
        url="postgresql+psycopg2://didasko_v1:segredo@postgres-v1:5432/didasko_v1",
        ambiente="homologacao",
    )
    assert url.endswith("/didasko_v1")


def test_seed_homolog_nao_vive_no_seed_de_producao():
    producao = (Path(__file__).resolve().parents[2] / "gsi_ebd" / "data" / "seed.py").read_text(
        encoding="utf-8"
    )
    homolog = (Path(__file__).resolve().parents[1] / "seed_homolog_estudo.py").read_text(encoding="utf-8")
    assert "aluno.fake.a@homolog.didasko.local" in homolog
    assert "aluno.fake.a@homolog.didasko.local" not in producao
    assert "seed_homolog_estudo" not in producao


def test_seed_homolog_recusa_ambiente_vazio():
    with pytest.raises(RuntimeError, match="homologacao"):
        recusar_producao(
            url="postgresql+psycopg2://didasko_v1:segredo@postgres:5432/didasko_v1",
            ambiente="",
        )


def test_seed_homolog_recusa_ambiente_desconhecido():
    with pytest.raises(RuntimeError, match="homologacao"):
        recusar_producao(
            url="postgresql+psycopg2://didasko_v1:segredo@postgres:5432/didasko_v1",
            ambiente="desenvolvimento",
        )


def test_popular_e_run_no_sqlite_didasko_v1(tmp_path, monkeypatch):
    inventario = tmp_path / "inventario.csv"
    inventario.write_text("id;decisao\nF-001;entra\n", encoding="utf-8")
    monkeypatch.setenv("CAMINHO_INVENTARIO", str(inventario))
    monkeypatch.setenv("DIDASKO_AMBIENTE", "homologacao")
    monkeypatch.setenv("SEED_PASSWORD", "Senha-homolog-123!")
    fontes._carregar.cache_clear()
    db = tmp_path / "didasko_v1.db"
    url = "sqlite:///" + db.resolve().as_posix()
    monkeypatch.setenv("DATABASE_URL", url)
    recusar_producao(url=url, ambiente="homologacao")
    senha = bcrypt.hashpw(b"Senha-teste-123!", bcrypt.gensalt(rounds=4)).decode()
    engine = criar_engine(url, connect_args={"check_same_thread": False})
    try:
        iniciar_banco(engine)
        with Session(engine) as session:
            admin = User(
                email="admin.seed@homolog.didasko.local",
                nome_base="Admin",
                nome_completo="Admin Seed",
                password_hash=senha,
                status=UserStatus.ATIVO,
                role=int(Role.ADMIN),
                must_change_password=False,
            )
            revisor = User(
                email="revisor.seed@homolog.didasko.local",
                nome_base="Revisor",
                nome_completo="Revisor Seed",
                password_hash=senha,
                status=UserStatus.ATIVO,
                role=int(Role.REVISOR),
                must_change_password=False,
            )
            session.add_all([admin, revisor])
            session.flush()
            obra = Obra(titulo="Obra de homologacao")
            versao = flow.importar(session, "F-001", obra, admin)
            session.add_all(
                [
                    ObraCapitulo(obra_id=obra.id, ordem=1, titulo="Capitulo", conteudo_md="Texto"),
                    Adendo(obra_id=obra.id, codigo="ADO-01", titulo="Nota", texto="Nota"),
                ]
            )
            session.flush()
            flow.revisar(session, versao, "Conferido", ["ok"], revisor, flow.hash_obra(session, obra.id))
            flow.liberar(session, versao, "Ajustes descritos", admin)
            session.commit()
            popular(session)
            session.commit()
            emails = {u.email for u in session.exec(select(User)).all()}
            assert ALUNOS_FAKE[0]["email"] in emails
            assert ALUNOS_FAKE[1]["email"] in emails
            aluno_a = session.exec(select(User).where(User.email == ALUNOS_FAKE[0]["email"])).one()
            aluno_b = session.exec(select(User).where(User.email == ALUNOS_FAKE[1]["email"])).one()
            assert session.exec(select(Estudo)).first() is not None
            assert session.exec(select(Study)).first() is not None
            assert session.exec(select(StudyAssignment).where(StudyAssignment.user_id == aluno_a.id)).first()
            assert session.exec(select(StudyAssignment).where(StudyAssignment.user_id == aluno_b.id)).first() is None
    finally:
        engine.dispose()
        fontes._carregar.cache_clear()
    run()
    engine = criar_engine(url, connect_args={"check_same_thread": False})
    try:
        with Session(engine) as session:
            aluno_a = session.exec(select(User).where(User.email == ALUNOS_FAKE[0]["email"])).one()
            assert session.exec(select(StudyAssignment).where(StudyAssignment.user_id == aluno_a.id)).first()
    finally:
        engine.dispose()


def test_popular_recusa_sem_obra_liberada(tmp_path, monkeypatch):
    monkeypatch.setenv("DIDASKO_AMBIENTE", "homologacao")
    monkeypatch.setenv("SEED_PASSWORD", "Senha-homolog-123!")
    db = tmp_path / "didasko_v1.db"
    url = "sqlite:///" + db.resolve().as_posix()
    recusar_producao(url=url, ambiente="homologacao")
    engine = criar_engine(url, connect_args={"check_same_thread": False})
    try:
        iniciar_banco(engine)
        with Session(engine) as session:
            with pytest.raises(RuntimeError, match="versao_liberada_id"):
                popular(session)
            assert session.exec(select(User).where(User.email == ALUNOS_FAKE[0]["email"])).first() is None
            assert session.exec(select(StudyAssignment)).first() is None
    finally:
        engine.dispose()
