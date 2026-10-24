"""Consultas agregadas dos paineis (so leitura)."""
from collections import defaultdict

from sqlmodel import Session, select

from gsi_ebd.models import (
    Ambiente,
    AmbienteEstudo,
    Equipe,
    EquipeInstrutor,
    Estudo,
    Obra,
    ObraVersao,
    ObraVersaoEvento,
    Progress,
    Role,
    Study,
    StudyAssignment,
    Turma,
    TurmaMembro,
    User,
    VinculoObra,
)

FILA_REVISAO = ("em_revisao", "aguardando_admin")
HISTORICO = ("vista", "recusada", "liberada")


def resumo_admin(session: Session) -> dict:
    obras = list(session.exec(select(Obra).order_by(Obra.id)))
    estudos = list(session.exec(select(Estudo).order_by(Estudo.id)))
    obras_em_estudo = {item.obra_id for item in estudos}
    estudos_por_id = {item.id: item for item in session.exec(select(Study))}
    users = {item.id: item for item in session.exec(select(User))}

    ambientes = list(session.exec(select(Ambiente)))
    ambiente_do_coord = {item.coordenador_id: item for item in ambientes}
    escolhas = list(session.exec(select(AmbienteEstudo)))
    vinculos = list(session.exec(select(VinculoObra)))
    equipes = list(session.exec(select(Equipe)))
    vinculos_inst = list(session.exec(select(EquipeInstrutor)))
    turmas = list(session.exec(select(Turma)))
    membros = list(session.exec(select(TurmaMembro)))
    atribuicoes = list(session.exec(select(StudyAssignment)))
    progressos = list(session.exec(select(Progress)))

    escolhas_por_amb = defaultdict(list)
    for escolha in escolhas:
        estudo = estudos_por_id.get(escolha.study_id)
        if estudo is not None:
            escolhas_por_amb[escolha.ambiente_id].append(estudo)

    obras_por_coord = defaultdict(list)
    obras_por_id = {item.id: item for item in obras}
    for vinculo in vinculos:
        obra = obras_por_id.get(vinculo.obra_id)
        if obra is not None:
            obras_por_coord[vinculo.coordenador_id].append(obra)

    inst_por_equipe = defaultdict(list)
    for vinculo in vinculos_inst:
        instrutor = users.get(vinculo.instrutor_id)
        if instrutor is not None:
            inst_por_equipe[vinculo.equipe_id].append(instrutor)

    alunos_por_turma = defaultdict(list)
    for membro in membros:
        aluno = users.get(membro.user_id)
        if aluno is not None:
            alunos_por_turma[membro.turma_id].append(aluno)

    turmas_por_inst = defaultdict(list)
    for turma in turmas:
        turmas_por_inst[turma.instrutor_id].append(turma)

    coordenadores = []
    for coord in session.exec(select(User).where(User.role == int(Role.COORDENADOR)).order_by(User.id)):
        ambiente = ambiente_do_coord.get(coord.id)
        instrutores_vistos = {}
        equipes_do_coord = [e for e in equipes if e.coordenador_id == coord.id]
        if ambiente is not None:
            equipes_do_coord += [e for e in equipes if e.ambiente_id == ambiente.id and e not in equipes_do_coord]
        for equipe in equipes_do_coord:
            for instrutor in inst_por_equipe.get(equipe.id, []):
                instrutores_vistos[instrutor.id] = instrutor
        for instrutor in users.values():
            if instrutor.role == int(Role.INSTRUTOR) and instrutor.coordenador_id == coord.id:
                instrutores_vistos[instrutor.id] = instrutor
        blocos = []
        for instrutor in sorted(instrutores_vistos.values(), key=lambda u: u.id or 0):
            alunos = []
            vistos = set()
            for turma in turmas_por_inst.get(instrutor.id, []):
                for aluno in alunos_por_turma.get(turma.id, []):
                    if aluno.id not in vistos:
                        vistos.add(aluno.id)
                        alunos.append(aluno)
            for aluno in users.values():
                if aluno.role == int(Role.ALUNO) and aluno.instrutor_id == instrutor.id and aluno.id not in vistos:
                    vistos.add(aluno.id)
                    alunos.append(aluno)
            blocos.append({"usuario": instrutor, "alunos": alunos})
        coordenadores.append(
            {
                "usuario": coord,
                "ambiente": ambiente,
                "estudos": escolhas_por_amb.get(ambiente.id, []) if ambiente else [],
                "obras": obras_por_coord.get(coord.id, []),
                "instrutores": blocos,
            }
        )

    atrib_por_aluno = defaultdict(list)
    for item in atribuicoes:
        atrib_por_aluno[item.user_id].append(item)
    prog_por_aluno = defaultdict(list)
    for item in progressos:
        prog_por_aluno[item.user_id].append(item)

    alunos = []
    for aluno in session.exec(select(User).where(User.role == int(Role.ALUNO)).order_by(User.id)):
        feitos, a_fazer = [], []
        for atrib in atrib_por_aluno.get(aluno.id, []):
            estudo = estudos_por_id.get(atrib.study_id)
            alvo = feitos if atrib.completed else a_fazer
            alvo.append({"atribuicao": atrib, "estudo": estudo})
        alunos.append(
            {
                "usuario": aluno,
                "feitos": feitos,
                "a_fazer": a_fazer,
                "progressos": prog_por_aluno.get(aluno.id, []),
            }
        )

    return {
        "obras_disponiveis": [
            o for o in obras if o.versao_liberada_id is not None and o.disponibilidade == "aberta"
        ],
        "obras_em_estudo": [o for o in obras if o.id in obras_em_estudo],
        "estudos": estudos,
        "coordenadores": coordenadores,
        "alunos": alunos,
    }


def resumo_revisor(session: Session) -> dict:
    fila = list(
        session.exec(
            select(Obra)
            .join(ObraVersao, ObraVersao.obra_id == Obra.id)
            .where(ObraVersao.status.in_(list(FILA_REVISAO)))
            .distinct()
        )
    )
    eventos = list(
        session.exec(
            select(ObraVersaoEvento)
            .where(ObraVersaoEvento.tipo.in_(list(HISTORICO)))
            .order_by(ObraVersaoEvento.quando.desc())
        )
    )
    versoes = {item.id: item for item in session.exec(select(ObraVersao))}
    obras = {item.id: item for item in session.exec(select(Obra))}
    autores = {item.id: item for item in session.exec(select(User))}
    historico = []
    for evento in eventos:
        versao = versoes.get(evento.versao_id)
        obra = obras.get(versao.obra_id) if versao is not None else None
        historico.append(
            {
                "evento": evento,
                "obra": obra,
                "versao": versao,
                "autor": autores.get(evento.autor_id),
            }
        )
    return {"fila": fila, "historico": historico}
