"""Correcao final: renomear meta_supervisores -> meta_instrutores e conferir."""
import sys, os, io
sys.dont_write_bytecode = True
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = r"C:\Projetos\EM_ESTUDO\EVANGELICOS\ESTUDOS_BIBLICOS\GSI_EBD"
sys.path.insert(0, ROOT); os.chdir(ROOT)
from rxconfig import config
from sqlalchemy import create_engine, text, inspect
eng = create_engine(str(config.db_url)); insp = inspect(eng)

with eng.connect() as con:
    con.rollback()
    uc = {x["name"] for x in insp.get_columns("user")}
    if "meta_supervisores" in uc and "meta_instrutores" not in uc:
        con.execute(text('ALTER TABLE "user" RENAME COLUMN meta_supervisores TO meta_instrutores'))
        print("  RENAME meta_supervisores -> meta_instrutores")
    elif "meta_instrutores" in uc:
        print("  meta_instrutores ja existe")

    # varredura: alguma outra coluna do modelo falta na producao?
    from sqlmodel import SQLModel
    import gsi_ebd.models  # noqa
    insp = inspect(eng)
    print("\n=== CONFERENCIA COMPLETA: modelo x producao ===")
    faltando = []
    for nome, tabela in sorted(SQLModel.metadata.tables.items()):
        if nome not in insp.get_table_names():
            faltando.append(f"TABELA {nome} AUSENTE"); continue
        prod = {x["name"] for x in insp.get_columns(nome)}
        for col in tabela.columns:
            if col.name not in prod:
                faltando.append(f"{nome}.{col.name} AUSENTE")
    if faltando:
        for f in faltando: print("  ", f)
        con.rollback()
    else:
        print("  nenhuma divergencia: producao == modelo")
    con.commit()
