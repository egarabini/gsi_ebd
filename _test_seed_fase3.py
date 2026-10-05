import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from sqlmodel import create_engine, SQLModel, Session, select
from gsi_ebd.data import seed
from gsi_ebd.models.study import Study, StudyStatus

engine = create_engine("sqlite:///_test_fase3.db")
SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    admin = seed.seed_admin(session)
    seed.seed_users(session, admin)
    seed.seed_studies(session, admin)

    estudos = session.exec(select(Study)).all()
    print("Total estudos:", len(estudos))
    for e in estudos:
        print(e.title, "->", e.status)

    pendentes = session.exec(
        select(Study).where(Study.status.in_([StudyStatus.PROPOSTO, StudyStatus.EM_REVISAO]))
    ).all()
    print("Pendentes:", [e.title for e in pendentes])

print("OK")
