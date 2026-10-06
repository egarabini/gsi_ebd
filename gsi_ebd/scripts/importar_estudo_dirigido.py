"""
Importa os capitulos do Estudo Dirigido para o GSI_EBD.

Fontes (arvore canonica definida pelo ARQUITETO):
  - PLANOS  : DOUTRINAS_CRISTAS/estudo_dirigido/capitulo_NN/plano-de-estudo.md
              (a versao mais refinada dos planos; derivada de Grudem_Doutrina_Biblica)
  - TEXTO   : Grudem_Doutrina_Biblica/Capitulo_NN/*_PT_v1.md  (arvore CANONICA)

O texto do capitulo NAO e gravado no banco: ele e traducao de obra protegida por
direitos autorais e o plano de estudo e autossuficiente (traz definicoes,
passagens a memorizar, objetivos, questoes e gabarito).

Gera:
  Study        -> um capitulo
  StudyVersion -> content_md (o plano) + questions_json (375 questoes tipadas)

Tipos de questao gerados (contrato de states/aluno.py):
  multiple_choice (1/cap, com gabarito) | fill_blank (1/cap) | open (aquecimento,
  dissertativas e reflexao — que a plataforma nao corrige sozinha)

Uso:
  python -m gsi_ebd.scripts.importar_estudo_dirigido --dry-run [--capitulo N] [--json]
  python -m gsi_ebd.scripts.importar_estudo_dirigido --autoteste   # SQLite descartavel
  python -m gsi_ebd.scripts.importar_estudo_dirigido --apply       # grava no banco do .env

Sem --apply/--autoteste nada e gravado.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# ── Caminhos ────────────────────────────────────────────────────────────────
def _achar_estudos_biblicos(inicio: Path) -> Path:
    for p in [inicio, *inicio.parents]:
        if (p / "GSI_EBD").is_dir() and (p / "DOUTRINAS_CRISTAS").is_dir():
            return p
    raise RuntimeError(f"Nao encontrei ESTUDOS_BIBLICOS a partir de {inicio}")


ROOT = Path(__file__).resolve().parents[2]            # .../GSI_EBD
ESTUDOS = _achar_estudos_biblicos(Path(__file__).resolve())
PLANOS_DIR = ESTUDOS / "DOUTRINAS_CRISTAS" / "estudo_dirigido"
GRUDEM_DIR = ESTUDOS / "Grudem_Doutrina_Biblica"

CATEGORIAS = {
    "I": "escrituras", "II": "deus", "III": "homem", "IV": "cristo",
    "V": "aplicacao-da-redencao", "VI": "igreja", "VII": "futuro",
}
NIVEIS = {1: "basico", 2: "basico", 3: "basico", 4: "medio"}


def _ler(p: Path) -> str:
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return p.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return p.read_text(encoding="utf-8", errors="replace")


# ── Utilidades de markdown ──────────────────────────────────────────────────
def _limpar(texto: str) -> str:
    """Remove sobras de markdown: checkboxes, separadores, headings."""
    texto = re.sub(r"(?m)^\s*-\s*\[ \].*$", "", texto)
    texto = re.sub(r"(?m)^\s*-{3,}\s*$", "", texto)
    texto = re.sub(r"(?m)^\s*#+.*$", "", texto)
    return re.sub(r"\s+", " ", texto).strip().strip("-").strip()


def _secao(texto: str, titulo_parcial: str, proximos: list[str]) -> str:
    """Recorta o trecho entre um heading que contenha `titulo_parcial` e o proximo heading conhecido."""
    i = -1
    for m in re.finditer(r"(?m)^##+\s+(.*)$", texto):
        if titulo_parcial in m.group(1):
            i = m.end()
            break
    if i < 0:
        return ""
    fim = len(texto)
    for m in re.finditer(r"(?m)^##+\s+(.*)$", texto[i:]):
        if any(p in m.group(1) for p in proximos):
            fim = i + m.start()
            break
    return texto[i:fim].strip()


# ── Extratores de questao ───────────────────────────────────────────────────
def _questoes_abertas(secao: str, prefixo: str, tipo: str = "open") -> list[dict]:
    """Extrai marcadores **qN.N** de uma secao como questoes abertas."""
    out = []
    for m in re.finditer(
        r"\*\*q(\d+)\.(\d+)\*\*\s*(.+?)(?=\n\*\*q\d+\.\d+\*\*|\n-\s*\[ \]|\n---|\Z)",
        secao, re.S,
    ):
        limpo = _limpar(m.group(3))
        if limpo:
            out.append({
                "key": f"{prefixo}_{m.group(1)}_{m.group(2)}",
                "type": tipo,
                "question": limpo,
                "answer": "",
            })
    return out


def _blocos(secao: str) -> list[tuple[str, str, str, list[tuple[str, str]]]]:
    """Divide a secao em blocos por marcador **qN.N**; detecta alternativas no bloco."""
    partes = re.split(r"(?m)^\*\*q(\d+)\.(\d+)\*\*", secao)
    out = []
    for i in range(1, len(partes) - 2, 3):
        cap, num, corpo = partes[i], partes[i + 1], partes[i + 2]
        opts = re.findall(r"-\s*\(.\)\s*([a-e])\)\s*(.+)", corpo)
        out.append((cap, num, corpo, opts))
    return out


def _questoes_parte_a(secao: str, gabarito: dict) -> list[dict]:
    """Classifica cada bloco da Parte A: alternativas => multiple_choice; senao fill_blank."""
    out = []
    for cap, num, corpo, opts in _blocos(secao):
        primeira = corpo.split("\n")[0]
        if opts:
            letra = gabarito.get(f"q{cap}.{num}", "")
            out.append({
                "key": f"mc_{cap}_{num}",
                "type": "multiple_choice",
                "question": _limpar(primeira),
                "options": [t.strip() for _, t in opts],
                "answer": next((t.strip() for l, t in opts if l == letra), ""),
                "gabarito_letra": letra,
            })
        else:
            limpo = _limpar(primeira)
            if limpo:
                out.append({
                    "key": f"fb_{cap}_{num}",
                    "type": "fill_blank",
                    "question": limpo,
                    "answer": "",
                })
    return out


def _parse_gabarito(texto: str) -> dict:
    return {f"q{m.group(1)}": m.group(2)
            for m in re.finditer(r"\*\*q(\d+\.\d+)\*\*:\s*\*\*([a-e])\)\*\*", texto)}


# ── Parser do capitulo ──────────────────────────────────────────────────────
def parse_plano(cap: int) -> dict | None:
    arq = PLANOS_DIR / f"capitulo_{cap:02d}" / "plano-de-estudo.md"
    if not arq.exists():
        return None
    t = _ler(arq)

    m_parte = re.search(r'parte:\s*"?([IVX]+)"?', t)
    m_titulo = re.search(r'titulo:\s*"?(.+?)"?\s*$', t, re.M)
    parte = m_parte.group(1) if m_parte else "I"
    titulo = m_titulo.group(1).strip() if m_titulo else f"Capitulo {cap:02d}"

    gabarito = _parse_gabarito(t)
    aquec = _secao(t, "Etapa 1", ["Etapa 2"])
    parte_a = _secao(t, "Parte A", ["Parte B", "Rubrica"])
    parte_b = _secao(t, "Parte B", ["Rubrica"])
    reflex = _secao(t, "Etapa 5", ["Etapa 6"])
    # Etapa 6 — Sintese em 3 frases. Nao usa o marcador **qN.N**, entao e montada aqui.
    sintese = _secao(t, "Etapa 6", ["Proximo", "Gabarito"])

    questoes = (
        _questoes_abertas(aquec, "aquec")
        + _questoes_parte_a(parte_a, gabarito)
        + _questoes_abertas(parte_b, "diss")
        + _questoes_abertas(reflex, "refl")
    )
    if sintese and re.search(r"(?m)^\s*1\.\s*_+", sintese):
        questoes.append({
            "key": "sint_6_1",
            "type": "open",
            "question": "Sintese do capitulo em 3 frases suas.",
            "answer": "",
        })

    # Conceitos: apenas a Etapa 3, ANTES da subsecao de passagens
    sec_conceitos = _secao(t, "Etapa 3", ["Passagens", "Etapa 4"])
    sec_passagens = _secao(t, "Passagens biblicas", ["Etapa 4"]) or _secao(t, "Passagens", ["Etapa 4"])
    padrao = r"(?m)^-\s*\[ \]\s*\*\*(.+?)\*\*\s*—\s*(.+)$"
    conceitos = re.findall(padrao, sec_conceitos)
    passagens = re.findall(padrao, sec_passagens)

    return {
        "capitulo": cap,
        "titulo": titulo,
        "parte": parte,
        "categoria": CATEGORIAS.get(parte, "geral"),
        "nivel": NIVEIS.get(cap, "basico"),
        "content_md": t,
        "questions": questoes,
        "conceitos": conceitos,
        "passagens": passagens,
        "totais": {
            "questoes": len(questoes),
            "objetivas": sum(1 for q in questoes if q["type"] == "multiple_choice"),
            "preenchimento": sum(1 for q in questoes if q["type"] == "fill_blank"),
            "abertas": sum(1 for q in questoes if q["type"] == "open"),
            "sem_resposta": sum(1 for q in questoes
                                if q["type"] == "multiple_choice" and not q["answer"]),
        },
    }


# ── Gravacao ────────────────────────────────────────────────────────────────
def gravar(dados: dict, engine) -> str:
    from sqlmodel import Session, select
    from ..models.study import Study, StudyVersion, StudyStatus

    titulo = f"Cap. {dados['capitulo']:02d} — {dados['titulo']}"
    with Session(engine) as s:
        if s.exec(select(Study).where(Study.title == titulo)).first():
            return "ja existia"
        st = Study(
            title=titulo,
            description=f"Parte {dados['parte']} — Estudo Dirigido (Doutrinas Cristas / Grudem)",
            category=dados["categoria"],
            level=dados["nivel"],
            status=StudyStatus.APROVADO,
            aprovado_por=1,
        )
        s.add(st)
        s.flush()
        sv = StudyVersion(
            study_id=st.id,
            version=1,
            content_md=dados["content_md"],
            questions_json=json.dumps(dados["questions"], ensure_ascii=False),
            target_audience="all",
        )
        s.add(sv)
        s.commit()
        return f"gravado (study={st.id}, version={sv.id})"


# ── CLI ─────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="Importa o Estudo Dirigido para o GSI_EBD")
    ap.add_argument("--capitulo", type=int, help="apenas este capitulo (1-34)")
    ap.add_argument("--dry-run", action="store_true", help="mostra o que faria, sem gravar")
    ap.add_argument("--apply", action="store_true", help="grava no banco do .env")
    ap.add_argument("--autoteste", action="store_true", help="grava em SQLite descartavel")
    ap.add_argument("--json", action="store_true", help="imprime as questoes do cap. 1")
    args = ap.parse_args()

    alvos = [args.capitulo] if args.capitulo else list(range(1, 35))
    planos = [(c, p) for c in alvos if (p := parse_plano(c))]

    print(f"Capitulos lidos: {len(planos)}/{len(alvos)}")
    print(f"{'cap':>4} {'quest':>6} {'MC':>4} {'FB':>4} {'AB':>4} {'s/resp':>7}  titulo")
    tot = {"questoes": 0, "objetivas": 0, "preenchimento": 0, "abertas": 0, "sem_resposta": 0}
    for c, p in planos:
        t = p["totais"]
        for k in tot:
            tot[k] += t[k]
        print(f"{c:>4} {t['questoes']:>6} {t['objetivas']:>4} {t['preenchimento']:>4} "
              f"{t['abertas']:>4} {t['sem_resposta']:>7}  {p['titulo'][:44]}")
    print(f"\nTOTAL: {tot['questoes']} questoes | {tot['objetivas']} objetivas | "
          f"{tot['preenchimento']} preenchimento | {tot['abertas']} abertas | "
          f"{tot['sem_resposta']} sem gabarito")

    if args.json and planos:
        print(f"\n--- capitulo {planos[0][0]} ---")
        print(json.dumps(planos[0][1]["questions"], ensure_ascii=False, indent=2)[:2000])

    if args.autoteste:
        import os, tempfile
        from sqlmodel import Session, create_engine, select, SQLModel
        os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
        db = Path(tempfile.gettempdir()) / "gsi_import_autoteste.db"
        db.unlink(missing_ok=True)
        eng = create_engine(f"sqlite:///{db.as_posix()}")
        import gsi_ebd.models  # noqa: F401  registra as tabelas no metadata
        SQLModel.metadata.create_all(eng)
        print(f"\n--- AUTOTESTE (SQLite descartavel) ---")
        for c, p in planos:
            print(f"  cap {c:02d}: {gravar(p, eng)}")
        from ..models.study import Study, StudyVersion
        with Session(eng) as s:
            ns = len(s.exec(select(Study)).all())
            vs = s.exec(select(StudyVersion)).all()
            print(f"  -> Studies: {ns} | versoes: {len(vs)}")
            if vs:
                q = json.loads(vs[0].questions_json)
                tipos = {}
                for x in q:
                    tipos[x["type"]] = tipos.get(x["type"], 0) + 1
                print(f"  -> 1a versao: {len(q)} questoes | tipos {tipos}")
                mc = next((x for x in q if x["type"] == "multiple_choice"), None)
                if mc:
                    print(f"  -> MC: {mc['question'][:58]}")
                    print(f"     opcoes={len(mc['options'])} resposta='{mc['answer'][:40]}'")
        db.unlink(missing_ok=True)
        print("  -> SQLite descartavel removido")

    if args.apply:
        if args.autoteste:
            print("ERRO: use --apply OU --autoteste, nao os dois.")
            return 2
        from rxconfig import config
        from sqlmodel import create_engine
        print(f"\n--- APPLY ({str(config.db_url).split('@')[-1]}) ---")
        eng = create_engine(config.db_url)
        for c, p in planos:
            print(f"  cap {c:02d}: {gravar(p, eng)}")

    if not (args.apply or args.autoteste):
        print("\n(dry-run: nada gravado. Use --apply ou --autoteste.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
