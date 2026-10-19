"""Contratos do seed e do primeiro login (DEM-202610-012)."""
from pathlib import Path
from secrets import token_urlsafe
import subprocess
from unittest.mock import Mock

import bcrypt
import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from gsi_ebd.data import seed
from gsi_ebd.models.user import Role, User
from gsi_ebd.states.auth import AuthState
from gsi_ebd.states import auth

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def senha_seed(monkeypatch):
    value = token_urlsafe(24)
    monkeypatch.setenv("SEED_PASSWORD", value)
    return value


@pytest.fixture
def banco(tmp_path):
    engine = create_engine("sqlite:///" + (tmp_path / "seed.db").as_posix())
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.mark.parametrize("value", [None, ""])
@pytest.mark.parametrize("populado", [False, True])
def test_rf02_seed_aborta_antes_de_acessar_banco(monkeypatch, banco, value, populado):
    if populado:
        with Session(banco) as session:
            session.add(User(email="existente@example.test"))
            session.commit()
    if value is None:
        monkeypatch.delenv("SEED_PASSWORD", raising=False)
    else:
        monkeypatch.setenv("SEED_PASSWORD", value)

    def proibido(*args, **kwargs):
        pytest.fail("Seed acessou o banco sem SEED_PASSWORD")

    monkeypatch.setattr("sqlmodel.create_engine", proibido)
    monkeypatch.setattr(seed, "Session", proibido)
    with pytest.raises(SystemExit, match="SEED_PASSWORD") as error:
        seed.run_seed()
    assert error.value.code != 0
    with Session(banco) as session:
        assert len(session.exec(select(User)).all()) == int(populado)


def test_rf01_rf03_seed_hash_troca_obrigatoria_e_log(monkeypatch, banco, senha_seed, capsys):
    monkeypatch.setattr("sqlmodel.create_engine", lambda *args, **kwargs: banco)
    seed.run_seed()
    with Session(banco) as session:
        users = session.exec(select(User)).all()
        assert len(users) == 5
        assert {user.role for user in users} == {Role.ADMIN, Role.COORDENADOR, Role.INSTRUTOR, Role.ALUNO}
        for user in users:
            assert user.must_change_password is True
            assert bcrypt.checkpw(senha_seed.encode(), user.password_hash.encode())
    assert senha_seed not in capsys.readouterr().out


def test_rf05_seed_preserva_usuarios_existentes(banco, senha_seed, monkeypatch):
    with Session(banco) as session:
        admin = seed.seed_admin(session)
        seed.seed_users(session, admin)
        for user in session.exec(select(User)).all():
            user.must_change_password = False
            user.nome_base = "Alterado pelo usuario"
            session.add(user)
        session.commit()
        def snapshot():
            return {u.email: (u.id, u.password_hash, u.must_change_password, u.nome_base)
                    for u in session.exec(select(User)).all()}
        before = snapshot()
        monkeypatch.setenv("SEED_PASSWORD", token_urlsafe(24))
        admin = seed.seed_admin(session)
        seed.seed_users(session, admin)
        assert before == snapshot()


@pytest.mark.parametrize("role", list(Role))
def test_rf03_login_encaminha_todos_inclusive_admin(banco, senha_seed, monkeypatch, role):
    with Session(banco) as session:
        user = User(email="login@example.test", role=role, status="ativo",
                    password_hash=seed.hash_password(senha_seed), must_change_password=True)
        session.add(user)
        session.commit()
        user_id = user.id
    monkeypatch.setattr(auth.rx, "session", lambda: Session(banco))
    redirect = Mock(return_value=object())
    monkeypatch.setattr(auth.rx, "redirect", redirect)
    state = AuthState(_reflex_internal_init=True)
    state.login_email = "login@example.test"
    state.login_password = senha_seed
    event = AuthState.login.fn(state)
    assert state.is_authenticated is True
    assert state.current_user_id == user_id
    assert state.must_change_password is True
    redirect.assert_called_once_with("/perfil/alterar-senha")
    assert event is redirect.return_value
    assert state.login_password == ""


def test_rf04_varredura_do_escopo():
    forbidden = "senha" + "123"
    files = [ROOT / name for name in (
        "gsi_ebd/data/seed.py", "README.md", "deploy/DEPLOY.md", "deploy/subir.sh",
    )]
    files.extend((ROOT / "tests").rglob("*.py"))
    assert not [str(path.relative_to(ROOT)) for path in files
                if forbidden in path.read_text(encoding="utf-8")]


def test_rf06_exemplo_sem_senha_real():
    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    assert [line for line in lines if line.startswith("SEED_PASSWORD=")] == ["SEED_PASSWORD="]


def test_rf07_deploy_nao_imprime_credenciais():
    script = (ROOT / "deploy/subir.sh").read_text(encoding="utf-8")
    assert 'echo "Login' not in script
    assert "admin@gsi.ebd" not in script


def test_rf04_varredura_repositorio_lista_excecoes():
    forbidden = "senha" + "123"
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, capture_output=True, check=True,
    )
    matches = []
    unexpected = []
    for name in sorted(set(result.stdout.decode("utf-8").split("\0")) - {""}):
        path = ROOT / name
        if not path.is_file() or path.suffix not in {".py", ".md", ".sh", ".yml", ".yaml", ".example"}:
            continue
        if forbidden not in path.read_text(encoding="utf-8-sig"):
            continue
        matches.append(name)
        allowed = (
            name in {"gsi_ebd/states/admin.py", "gsi_ebd/pages/admin.py"}
            or (name.startswith("Diagnostico/") and path.suffix == ".md")
            or name.startswith("documentacao/adr/ADR-008")
            or name.startswith("documentacao/dem/")
            or "/eval/" in name
        )
        if not allowed:
            unexpected.append(name)
    print("Excecoes historicas encontradas:", matches)
    assert unexpected == [], unexpected
