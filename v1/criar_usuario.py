"""Bootstrap local explicito; nunca e executado pelo boot da app."""
import argparse
from getpass import getpass
from sqlmodel import Session, select
from gsi_ebd.models import User, Role
from v1.auth import hash_senha
from v1.db import criar_engine, iniciar_banco


def criar_usuario(session, email, papel, senha):
    if len(senha) < 8 or len(senha.encode()) > 72 or "@" not in email:
        raise ValueError("Email ou senha invalidos")
    if session.exec(select(User).where(User.email == email)).first():
        raise ValueError("Usuario ja existe; bootstrap nao altera contas")
    user = User(email=email, role=papel, status="ativo", password_hash=hash_senha(senha), must_change_password=True)
    session.add(user)
    session.commit()
    return user.id


def main():
    parser = argparse.ArgumentParser(description="Cria usuario local da v1 com troca obrigatoria")
    parser.add_argument("email")
    parser.add_argument("--papel", choices=["ADMIN", "REVISOR"], default="ADMIN")
    args = parser.parse_args()
    senha = getpass("Senha inicial (nao sera exibida): ")
    if senha != getpass("Confirme a senha: "):
        raise SystemExit("Senhas diferentes")
    engine = criar_engine()
    try:
        iniciar_banco(engine)
        with Session(engine) as session:
            criar_usuario(session, args.email.strip(), Role[args.papel], senha)
        print("Usuario criado com troca obrigatoria de senha.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
