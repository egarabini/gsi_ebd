"""
Seed inicial do banco de dados GSI-EBD.
Cria dados de exemplo para todos os roles e conteúdo da landing page.

Uso:
    python -m gsi_ebd.data.seed
"""
from datetime import date, datetime, timedelta
import json
import sys
import os

import bcrypt
import reflex as rx
from sqlmodel import Session, select

# Garante que o pacote raiz está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gsi_ebd.models.user import User, Role, UserStatus
from gsi_ebd.models.study import Study, StudyVersion, StudyAssignment, StudyLevel, StudyStatus
from gsi_ebd.models.turma import (Ambiente, Equipe, EquipeInstrutor, Turma, TurmaMembro)
from gsi_ebd.models.subscription import Subscription, PaymentHistory, SubscriptionStatus, PaymentMethod
from gsi_ebd.models.lead import Lead, LeadStatus
from gsi_ebd.models.site_content import Testemunho, SiteConfig
from gsi_ebd.models.notification import Notification, NotificationType
from gsi_ebd.models.progress import UserResponse, Progress


DEFAULT_PASSWORD = "senha123"
ADMIN_EMAIL = "admin@gsi.ebd"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def get_or_create_engine():
    from rxconfig import config
    from sqlmodel import create_engine
    db_url = config.db_url or "sqlite:///gsi_ebd.db"
    return create_engine(db_url)


def seed_site_config(session: Session):
    """Popula textos dinâmicos da landing page."""
    configs = [
        ("hero_titulo", "Cresça na Palavra — A qualquer hora, em qualquer lugar", "Título principal do Hero"),
        ("hero_subtitulo", "Uma plataforma de estudos bíblicos dirigidos, com acompanhamento personalizado para cada etapa da sua jornada de fé.", "Subtítulo do Hero"),
        ("hero_cta_texto", "Quero Participar", "Texto do botão CTA"),
        ("sobre_titulo", "Sobre a Plataforma GSI-EBD", "Título da seção Sobre"),
        ("sobre_texto", "O GSI-EBD (Estudos Bíblicos Dirigidos) é uma plataforma criada para facilitar o crescimento espiritual de forma estruturada, guiada e progressiva. Acreditamos que o estudo sistemático da Palavra transforma vidas.", "Texto da seção Sobre"),
        ("missao_texto", "Nossa missão é conectar pessoas à Palavra de Deus por meio de estudos estruturados, acompanhamento personalizado e comunidade.", "Texto de Missão"),
        ("visao_texto", "Ser a referência em estudos bíblicos digitais no Brasil, formando discípulos comprometidos com a Escritura.", "Texto de Visão"),
        ("planos_descricao", "Escolha o plano que melhor se adapta à sua jornada. Todos incluem acesso completo à plataforma e acompanhamento personalizado.", "Descrição geral dos planos"),
        ("niveis_basico_desc", "Fundamentos da fé — ideal para quem está iniciando a jornada bíblica.", "Descrição nível Básico"),
        ("niveis_medio_desc", "Aprofundamento doutrinário — para quem já domina os fundamentos.", "Descrição nível Médio"),
        ("niveis_avancado_desc", "Hermenêutica e teologia — para estudo avançado e contextualização.", "Descrição nível Avançado"),
        ("niveis_master_desc", "Especialização e liderança — para formação de líderes e coordenadores de fé.", "Descrição nível Master"),
        ("rodape_email", "contato@gsi-ebd.com.br", "Email de contato no rodapé"),
        ("rodape_telefone", "(00) 00000-0000", "Telefone de contato no rodapé"),
        ("redes_instagram", "", "URL Instagram"),
        ("redes_youtube", "", "URL YouTube"),
        ("redes_whatsapp", "", "URL ou número WhatsApp"),
        ("redes_facebook", "", "URL Facebook"),
    ]
    for chave, valor, descricao in configs:
        existing = session.exec(select(SiteConfig).where(SiteConfig.chave == chave)).first()
        if not existing:
            session.add(SiteConfig(chave=chave, valor=valor, descricao=descricao))
    session.commit()
    print("✅ SiteConfig populado")


def seed_testemunhos(session: Session):
    """Cria testemunhos de exemplo para a landing page."""
    if session.exec(select(Testemunho)).first():
        print("⏭️  Testemunhos já existem — pulando")
        return

    testemunhos = [
        Testemunho(
            nome="Maria Silva",
            cidade="São Paulo",
            estado="SP",
            profissao_fe="Adventista",
            texto="Os estudos bíblicos dirigidos transformaram minha vida espiritual. O acompanhamento personalizado fez toda a diferença na minha compreensão da Palavra.",
            ordem=1,
        ),
        Testemunho(
            nome="João Santos",
            cidade="Belo Horizonte",
            estado="MG",
            profissao_fe="Batista",
            texto="Nunca imaginei que seria possível estudar a Bíblia de forma tão estruturada e com tanto apoio. Estou no nível Avançado e não paro mais!",
            ordem=2,
        ),
        Testemunho(
            nome="Ana Rodrigues",
            cidade="Curitiba",
            estado="PR",
            profissao_fe="Presbiteriana",
            texto="Como coordenadora, posso acompanhar de perto o crescimento dos meus alunos. A plataforma facilita demais meu trabalho pastoral.",
            ordem=3,
        ),
    ]
    for t in testemunhos:
        session.add(t)
    session.commit()
    print("✅ Testemunhos criados")


def seed_leads(session: Session):
    """Cria um lead de exemplo."""
    if session.exec(select(Lead)).first():
        print("⏭️  Leads já existem — pulando")
        return

    session.add(Lead(
        nome="Pedro Almeida",
        email="pedro.almeida@exemplo.com",
        telefone="(11) 99999-0001",
        cidade="Campinas",
        estado="SP",
        membro_igreja=True,
        nome_igreja="Igreja Adventista do 7º Dia",
        denominacao="Adventista",
        mensagem="Tenho interesse em participar da plataforma como Coordenador de estudos para minha comunidade.",
        status=LeadStatus.PENDENTE,
    ))
    session.commit()
    print("✅ Lead de exemplo criado")


def seed_admin(session: Session) -> User:
    """Cria o Admin padrão (sem assinatura — Admin não paga)."""
    existing = session.exec(select(User).where(User.email == ADMIN_EMAIL)).first()
    if existing:
        print("⏭️  Admin já existe — pulando")
        return existing

    admin = User(
        nome_completo="Administrador do Sistema",
        nome_base="Admin",
        cpf="000.000.000-00",
        data_nascimento=date(1980, 1, 1),
        sexo="M",
        profissao_fe="",
        auto_descricao="Administrador da plataforma GSI-EBD",
        escolaridade="superior",
        cep="00000-000",
        logradouro="Rua do Sistema",
        numero="1",
        complemento="",
        bairro="Centro",
        cidade="São Paulo",
        estado="SP",
        email=ADMIN_EMAIL,
        telefone="(11) 00000-0000",
        password_hash=hash_password(DEFAULT_PASSWORD),
        must_change_password=False,  # Admin não precisa trocar
        role=Role.ADMIN,
        status=UserStatus.ATIVO,  # Admin sempre ATIVO
        assinatura_ativa=True,  # Admin não paga, mas flag ativa para não bloquear acesso
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    print(f"✅ Admin criado: {ADMIN_EMAIL} / {DEFAULT_PASSWORD}")
    return admin


def create_subscription(session: Session, user: User, admin_id: int) -> Subscription:
    """Cria uma assinatura ativa simulada para o usuário."""
    sub = Subscription(
        user_id=user.id,
        valor=29.90,
        status=SubscriptionStatus.ATIVA,
        data_inicio=date.today(),
        data_vencimento=date.today() + timedelta(days=30),
        data_pagamento=date.today(),
        metodo_pagamento=PaymentMethod.SIMULADO,
        referencia_externa=f"SIM-{user.id:04d}-{date.today().strftime('%Y%m%d')}",
        observacoes="Assinatura simulada — seed inicial",
        criado_por=admin_id,
    )
    session.add(sub)
    session.flush()

    # Registra no histórico
    session.add(PaymentHistory(
        subscription_id=sub.id,
        user_id=user.id,
        valor_pago=29.90,
        data_pagamento=date.today(),
        metodo=PaymentMethod.SIMULADO,
        referencia=sub.referencia_externa,
        registrado_por=admin_id,
        observacoes="Pagamento inicial simulado — seed",
    ))
    return sub


def seed_users(session: Session, admin: User):
    """Cria usuários de exemplo para cada role."""


    # --- COORDENADOR ---
    coordenador_email = "coordenador@gsi.ebd"
    coordenador = session.exec(select(User).where(User.email == coordenador_email)).first()
    if not coordenador:
        coordenador = User(
            nome_completo="Ana Coordenadora Ferreira",
            nome_base="Ana",
            cpf="222.222.222-22",
            data_nascimento=date(1990, 7, 22),
            sexo="F",
            profissao_fe="Batista",
            auto_descricao="Coordenadora comprometida com o crescimento espiritual dos alunos.",
            escolaridade="superior",
            cep="30130-010",
            logradouro="Avenida Afonso Pena",
            numero="500",
            complemento="",
            bairro="Centro",
            cidade="Belo Horizonte",
            estado="MG",
            email=coordenador_email,
            telefone="(31) 99999-0003",
            password_hash=hash_password(DEFAULT_PASSWORD),
            must_change_password=False,   # usuário de teste — sem troca obrigatória
            role=Role.COORDENADOR,
            meta_instrutores=5,
            meta_alunos=50,
            status="ativo",               # usuário de teste — já ATIVO
            status_reason="Usuário de demonstração criado pelo seed",
            assinatura_ativa=True,
        )
        session.add(coordenador)
        session.flush()
        create_subscription(session, coordenador, admin.id)
        print(f"✅ Coordenador criado: {coordenador_email} / {DEFAULT_PASSWORD}")
    else:
        print("⏭️  Coordenador já existe — pulando")
        coordenador = session.exec(select(User).where(User.email == coordenador_email)).first()

    # --- AMBIENTE (tenant do Coordenador: isolamento + identidade visual) ---
    ambiente = session.exec(select(Ambiente).where(
        Ambiente.coordenador_id == coordenador.id)).first()
    if not ambiente:
        ambiente = Ambiente(
            nome="Ambiente Demonstracao",
            slug="demo",
            coordenador_id=coordenador.id,
            logo_url="",
            cor_primaria="#7c3aed",
            cor_secundaria="#4f46e5",
            tipografia="Inter",
            landing_titulo="Estudos Biblicos Dirigidos",
            landing_subtitulo="Aprenda a Palavra com acompanhamento de verdade.",
            landing_ativa=False,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        session.add(ambiente)
        session.flush()
        print(f"[ok] Ambiente criado: {ambiente.nome} (id={ambiente.id})")
        coordenador.ambiente_id = ambiente.id
        session.add(coordenador)
        session.flush()

    # --- INSTRUTOR (acompanha e corrige os alunos) ---
    instrutor_email = "instrutor@gsi.ebd"
    instrutor = session.exec(select(User).where(User.email == instrutor_email)).first()
    if not instrutor:
        instrutor = User(
            nome_completo="Paulo Instrutor Mendes",
            nome_base="Paulo",
            cpf="555.555.555-55",
            data_nascimento=date(1985, 3, 12),
            sexo="M",
            profissao_fe="Presbiteriana",
            auto_descricao="Instrutor dedicado a acompanhar cada aluno de perto.",
            escolaridade="pos_graduacao",
            cep="30130-010",
            logradouro="Avenida Afonso Pena",
            numero="500",
            complemento="",
            bairro="Centro",
            cidade="Belo Horizonte",
            estado="MG",
            email=instrutor_email,
            telefone="(31) 99999-0004",
            password_hash=hash_password(DEFAULT_PASSWORD),
            must_change_password=False,
            role=Role.INSTRUTOR,
            coordenador_id=coordenador.id,   # responde ao Coordenador
            ambiente_id=ambiente.id,
            meta_alunos=15,
            status="ativo",
            status_reason="Usuario de demonstracao criado pelo seed",
            assinatura_ativa=True,
        )
        session.add(instrutor)
        session.flush()
        create_subscription(session, instrutor, admin.id)
        print(f"[ok] Instrutor criado: {instrutor_email} / {DEFAULT_PASSWORD}")
    else:
        print("[..] Instrutor ja existe - pulando")

    # --- EQUIPE (entre o Coordenador e o Instrutor: separa por nivel de estudo) ---
    equipe = session.exec(select(Equipe).where(
        Equipe.coordenador_id == coordenador.id)).first()
    if not equipe:
        equipe = Equipe(
            nome="Equipe Basico",
            descricao="Instrutores que acompanham os alunos do nivel Basico.",
            coordenador_id=coordenador.id,
            ambiente_id=ambiente.id,
            nivel="basico",
            is_active=True,
            created_at=datetime.utcnow(),
        )
        session.add(equipe)
        session.flush()
        print("[ok] Equipe criada: Equipe Basico (nivel basico)")
    if instrutor and equipe:
        vinculo = session.exec(select(EquipeInstrutor).where(
            EquipeInstrutor.equipe_id == equipe.id,
            EquipeInstrutor.instrutor_id == instrutor.id)).first()
        if not vinculo:
            session.add(EquipeInstrutor(equipe_id=equipe.id, instrutor_id=instrutor.id))
            session.flush()
            print("[ok] Instrutor vinculado a Equipe Basico")

    # --- ALUNOS ---
    alunos_data = [
        ("aluno1@gsi.ebd", "Lucas Aluno Pereira", "Lucas", "333.333.333-33", date(1998, 11, 5), "M"),
        ("aluno2@gsi.ebd", "Beatriz Aluna Costa", "Bia", "444.444.444-44", date(2000, 4, 18), "F"),
    ]
    for email, nome_completo, nome_base, cpf, nasc, sexo in alunos_data:
        existing = session.exec(select(User).where(User.email == email)).first()
        if not existing:
            aluno = User(
                nome_completo=nome_completo,
                nome_base=nome_base,
                cpf=cpf,
                data_nascimento=nasc,
                sexo=sexo,
                profissao_fe="Protestante",
                auto_descricao="Aluno iniciante nos estudos bíblicos.",
                escolaridade="medio",
                cep="80010-000",
                logradouro="Rua XV de Novembro",
                numero="200",
                complemento="",
                bairro="Centro",
                cidade="Curitiba",
                estado="PR",
                email=email,
                telefone="(41) 99999-0000",
                password_hash=hash_password(DEFAULT_PASSWORD),
                must_change_password=False,   # usuário de teste — sem troca obrigatória
                role=Role.ALUNO,
                instrutor_id=instrutor.id,       # quem o acompanha e corrige
                coordenador_id=coordenador.id,
                ambiente_id=ambiente.id,         # fronteira do tenant
                is_active=True,
                status="ativo",               # usuário de teste — já ATIVO
                status_reason="Usuário de demonstração criado pelo seed",
                assinatura_ativa=True,
            )
            session.add(aluno)
            session.flush()
            create_subscription(session, aluno, admin.id)
            print(f"✅ Aluno criado: {email} / {DEFAULT_PASSWORD}")
        else:
            print(f"⏭️  Aluno {email} já existe — pulando")

    session.commit()


def seed_studies(session: Session, admin: User, coordenador_email: str = "coordenador@gsi.ebd"):
    """Cria estudos de exemplo para cada nível."""
    if session.exec(select(Study)).first():
        print("⏭️  Estudos já existem — pulando")
        return

    coordenador = session.exec(select(User).where(User.email == coordenador_email)).first()
    coordenador_id = coordenador.id if coordenador else None

    estudos = [
        {
            "title": "O Plano da Salvação",
            "description": "Fundamentos da salvação: pecado, graça, redenção e vida eterna.",
            "category": "doutrina",
            "level": StudyLevel.BASICO,
            "content_md": """# O Plano da Salvação

## Introdução

Desde o princípio, Deus planejou a redenção da humanidade...

## Versículos-Chave

- **João 3:16** — "Porque Deus amou o mundo de tal maneira..."
- **Romanos 3:23** — "Todos pecaram e estão destituídos da glória de Deus"
- **Efésios 2:8-9** — "Pela graça sois salvos, mediante a fé..."

## Conteúdo

O plano da salvação revela o amor infinito de Deus por cada ser humano...
""",
            "questions": [
                {"key": "q1", "type": "fill_blank", "question": "João 3:16 diz que Deus amou o ___", "answer": "mundo"},
                {"key": "q2", "type": "true_false", "question": "A salvação é obtida por obras humanas.", "answer": "false"},
                {"key": "q3", "type": "multiple_choice", "question": "O que significa 'graça'?", "options": ["Favor imerecido de Deus", "Recompensa por boas obras", "Obediência à lei"], "answer": "Favor imerecido de Deus"},
            ],
        },
        {
            "title": "A Palavra de Deus",
            "description": "A Bíblia como revelação divina: inspiração, cânon e interpretação.",
            "category": "hermeneutica",
            "level": StudyLevel.MEDIO,
            "content_md": """# A Palavra de Deus

## A Inspiração das Escrituras

**2 Timóteo 3:16** — "Toda a Escritura é inspirada por Deus..."

## O Processo de Formação do Cânon

Como os livros da Bíblia foram reconhecidos como sagrados...
""",
            "questions": [
                {"key": "q1", "type": "fill_blank", "question": "2 Timóteo 3:16 afirma que toda Escritura é ___ por Deus", "answer": "inspirada"},
                {"key": "q2", "type": "multiple_choice", "question": "Quantos livros tem a Bíblia protestante?", "options": ["66", "73", "39"], "answer": "66"},
            ],
        },
        {
            "title": "Hermenêutica Bíblica",
            "description": "Princípios e métodos de interpretação das Escrituras.",
            "category": "hermeneutica",
            "level": StudyLevel.AVANCADO,
            "content_md": """# Hermenêutica Bíblica

## O que é Hermenêutica?

A hermenêutica é a ciência e arte de interpretar textos, especialmente os sagrados...

## Princípios Fundamentais

1. **Contexto histórico-cultural**
2. **Contexto literário**
3. **Analogia da fé**
""",
            "questions": [
                {"key": "q1", "type": "open", "question": "Explique o princípio de analogia da fé na interpretação bíblica.", "answer": ""},
            ],
        },
        {
            "title": "Teologia Sistemática — Introdução",
            "description": "Fundamentos da teologia sistemática: método, divisões e história.",
            "category": "teologia",
            "level": StudyLevel.MASTER,
            "content_md": """# Teologia Sistemática

## Definição e Método

A teologia sistemática organiza as doutrinas bíblicas em um sistema coerente...

## Divisões Clássicas

- **Bibliologia** — Doutrina das Escrituras
- **Teologia Própria** — Doutrina de Deus
- **Cristologia** — Doutrina de Cristo
- **Pneumatologia** — Doutrina do Espírito Santo
- **Soteriologia** — Doutrina da Salvação
- **Escatologia** — Doutrina das últimas coisas
""",
            "questions": [
                {"key": "q1", "type": "multiple_choice", "question": "Qual divisão da teologia trata do Espírito Santo?", "options": ["Pneumatologia", "Cristologia", "Soteriologia"], "answer": "Pneumatologia"},
                {"key": "q2", "type": "open", "question": "Por que a organização sistemática das doutrinas é importante?", "answer": ""},
            ],
        },
        {
            "title": "Escatologia Bíblica",
            "description": "Estudo proposto sobre os eventos futuros segundo as Escrituras.",
            "category": "teologia",
            "level": StudyLevel.AVANCADO,
            "content_md": """# Escatologia Bíblica

## O que é Escatologia?

Escatologia é o estudo das últimas coisas: a volta de Cristo, o juízo final e a eternidade...

## Principais Correntes

- Pré-milenismo
- Pós-milenismo
- Amilenismo
""",
            "questions": [
                {"key": "q1", "type": "open", "question": "Qual a importância de estudar escatologia para a vida cristã?", "answer": ""},
            ],
            "status": StudyStatus.PROPOSTO,
        },
    ]

    for i, estudo_data in enumerate(estudos):
        status = estudo_data.get("status", StudyStatus.APROVADO)
        study = Study(
            title=estudo_data["title"],
            description=estudo_data["description"],
            category=estudo_data["category"],
            level=estudo_data["level"],
            status=status,
            proposto_por=coordenador_id,
            aprovado_por=admin.id if status == StudyStatus.APROVADO else None,
            approved_at=datetime.utcnow() if status == StudyStatus.APROVADO else None,
            is_active=True,
        )
        session.add(study)
        session.flush()

        version = StudyVersion(
            study_id=study.id,
            version=1,
            content_md=estudo_data["content_md"],
            questions_json=json.dumps(estudo_data["questions"], ensure_ascii=False),
        )
        session.add(version)

        print(f"✅ Estudo '{study.title}' ({study.level}) criado — status {status}")

    session.commit()


def seed_notification(session: Session, user: User, titulo: str, mensagem: str, tipo: str):
    """Cria notificação de boas-vindas."""
    session.add(Notification(
        user_id=user.id,
        tipo=tipo,
        titulo=titulo,
        mensagem=mensagem,
        link="/",
    ))


def seed_turmas(session: Session):
    """Cria a Turma de exemplo, vinculando Coordenador, INSTRUTOR, equipe e alunos."""
    if session.exec(select(Turma)).first():
        print("[..] Turmas ja existem - pulando")
        return

    coordenador = session.exec(select(User).where(User.email == "coordenador@gsi.ebd")).first()
    instrutor = session.exec(select(User).where(User.email == "instrutor@gsi.ebd")).first()
    equipe = session.exec(select(Equipe).where(Equipe.coordenador_id == coordenador.id)).first() \
        if coordenador else None
    estudo = session.exec(select(Study).where(Study.title == "O Plano da Salvação")).first()
    alunos = session.exec(
        select(User).where(User.email.in_(["aluno1@gsi.ebd", "aluno2@gsi.ebd"]))
    ).all()

    if not coordenador or not instrutor:
        print("[..] Coordenador/Instrutor nao encontrados - pulando seed de Turma")
        return

    turma = Turma(
        nome="Turma Fundamentos da Fé — 2026",
        descricao="Turma piloto de estudos bíblicos dirigidos, nível Básico.",
        instrutor_id=instrutor.id,
        coordenador_id=coordenador.id,
        equipe_id=equipe.id if equipe else None,
        ambiente_id=coordenador.ambiente_id,
        study_id=estudo.id if estudo else None,
        data_inicio=date.today(),
        is_active=True,
    )
    session.add(turma)
    session.flush()

    for aluno in alunos:
        session.add(TurmaMembro(
            turma_id=turma.id,
            user_id=aluno.id,
            data_entrada=date.today(),
            is_active=True,
        ))

    session.commit()
    print(f"✅ Turma '{turma.nome}' criada com {len(alunos)} aluno(s)")


def run_seed():
    print("\n🌱 Iniciando seed do banco GSI-EBD...\n")

    from rxconfig import config
    from sqlmodel import create_engine, SQLModel as _SQLModel

    db_url = config.db_url or "sqlite:///gsi_ebd.db"
    engine = create_engine(db_url)

    # Cria todas as tabelas (se não existirem)
    _SQLModel.metadata.create_all(engine)
    print("✅ Tabelas criadas/verificadas\n")

    with Session(engine) as session:
        seed_site_config(session)
        seed_testemunhos(session)
        seed_leads(session)
        admin = seed_admin(session)
        seed_users(session, admin)
        seed_studies(session, admin)
        seed_turmas(session)

    print("\n🎉 Seed concluído!\n")
    print("Credenciais de acesso:")
    print(f"  Admin:      {ADMIN_EMAIL} / {DEFAULT_PASSWORD}")
    print("  Coordenador:     coordenador@gsi.ebd / senha123")
    print("  Coordenador: coordenador@gsi.ebd / senha123  (role=COORDENADOR)")
    print("  Aluno 1:    aluno1@gsi.ebd / senha123")
    print("  Aluno 2:    aluno2@gsi.ebd / senha123")


if __name__ == "__main__":
    run_seed()