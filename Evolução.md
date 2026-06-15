**Ótimo, Eduardo!** Vamos estruturar o **gsi_ebd** de forma profissional, alinhada ao seu stack (Python puro, Reflex, Postgres, Docker/Traefik, Ollama/LangChain, Keycloak-like hierarchy).

### 1. Arquitetura Recomendada (RBAC + Hierarquia de Cadastro)

**Perfis (Roles):**
- **1 - Administrador**: Cadastra Supervisores e Gestores. Acesso total (configurações globais, relatórios agregados).
- **2 - Supervisor**: Visualiza relatórios de múltiplos Gestores.
- **3 - Gestor**: Cadastra e gerencia seus Alunos. Atribui estudos.
- **4 - Aluno**: Acessa apenas seus estudos, faz lições, vê progresso pessoal.

**Hierarquia de cadastro**:
- Admin → Gestores (e Supervisores)
- Gestor → Alunos (com vínculo `gestor_id`)

**Estudos**:
- Versões de lições (`StudyVersion`)
- Disponibilidade (`is_active`, `available_from`, `available_until`, `target_audience`)
- Atribuição por Gestor/Aluno (muitos-para-muitos ou via `UserStudyAssignment`)

### 2. Estrutura de Diretórios (atualizada para o repo)

```bash
gsi_ebd/
├── gsi_ebd/                  # Pacote principal (Reflex app)
│   ├── __init__.py
│   ├── rxconfig.py           # Config + DB URL
│   ├── main.py               # App entry + pages
│   ├── models/               # SQLModel / rx.Model
│   │   ├── __init__.py
│   │   ├── user.py           # User com role, gestor_id, etc.
│   │   ├── study.py          # Study, StudyVersion, StudyContent
│   │   ├── progress.py       # UserResponse, Progress, DifficultyLog
│   │   └── assignment.py     # Atribuições
│   ├── states/               # States Reflex
│   │   ├── auth.py
│   │   ├── admin.py
│   │   ├── gestor.py
│   │   ├── aluno.py
│   │   └── common.py
│   ├── components/           # UI reutilizáveis
│   ├── pages/                # Páginas por role
│   ├── services/             # AI, Bible API, etc.
│   ├── ai/                   # LangGraph agents (explicador, avaliador, etc.)
│   ├── utils/                # RBAC decorators, permissions
│   └── data/                 # Seeds iniciais (lições JSON/MD)
├── alembic/                  # Migrações (gerado pelo reflex db init)
├── tests/
├── docker-compose.yml        # Postgres + App + Traefik (seu estilo)
├── .env.example
├── requirements.txt / pyproject.toml (UV)
└── README.md
```

### 3. Configuração Inicial (faça isso agora)

1. **Clone e setup**:
   ```bash
   git clone https://github.com/egarabini/gsi_ebd.git
   cd gsi_ebd
   uv venv
   uv pip install reflex reflex-local-auth psycopg2-binary python-dotenv langchain ollama
   reflex init   # se ainda não rodou
   ```

2. **rxconfig.py** (Postgres):
   ```python
   import os
   from dotenv import load_dotenv
   import reflex as rx

   load_dotenv()

   config = rx.Config(
       app_name="gsi_ebd",
       db_url=os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/gsi_ebd"),
       # ... tailwind, etc.
   )
   ```

3. **.env** (adicione ao .gitignore):
   ```
   DATABASE_URL=postgresql://postgres:senha@localhost:5432/gsi_ebd
   # Ollama, etc.
   ```

4. **Inicializar DB**:
   ```bash
   reflex db init
   reflex db makemigrations --message "initial"
   reflex db migrate
   ```

### 4. Modelos Principais (SQLModel)

**models/user.py** (exemplo simplificado):
```python
import reflex as rx
from sqlmodel import Field, Relationship
from enum import Enum

class Role(int, Enum):
    ADMIN = 1
    SUPERVISOR = 2
    GESTOR = 3
    ALUNO = 4

class User(rx.Model, table=True):
    id: int = Field(primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str = Field(exclude=True)  # handled by reflex-local-auth
    nome: str
    role: Role = Field(default=Role.ALUNO)
    gestor_id: int | None = Field(foreign_key="user.id", nullable=True)  # hierarquia
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    gestor: "User" = Relationship(back_populates="alunos")
    alunos: list["User"] = Relationship(back_populates="gestor")
```

**Estudos**:
- `Study` (título, descrição, categoria)
- `StudyVersion` (versão, conteúdo Markdown/JSON, study_id)
- `StudyAssignment` (user_id, study_version_id, assigned_by, due_date)

### 5. Autenticação (reflex-local-auth)

Instale: `uv pip install reflex-local-auth`

Use o padrão dele + extendemos com `role` e hierarquia.

Em `states/auth.py`:
- Login/Register customizado
- Middleware ou State var para checar role (`@rx.var def current_user_role(self)`)

**RBAC simples** (em utils ou decorator):
```python
def require_role(min_role: Role):
    def decorator(fn):
        # checa no state
        ...
    return decorator
```

Páginas condicionais:
```python
rx.cond(
    AuthState.user.role == Role.ADMIN,
    admin_dashboard(),
    ...
)
```

### 6. Próximos Passos Imediatos

1. **Crie os modelos base** (User + Role + Study).
2. **Integre reflex-local-auth** com campos extras (role, gestor_id).
3. **Seed inicial**: Admin padrão + algumas lições da SGI7.
4. **Dashboard por role** (4 telas principais).
5. **IA**: Agente para contexto + geração de questões adaptativas (LangGraph como no Intellicare).

Quer que eu gere agora os arquivos iniciais diretamente no repo (via código que você pode copiar ou eu ajudo com commits)? Posso começar com:

- `rxconfig.py` + models completos
- `states/auth.py` com reflex-local-auth
- Docker Compose pronto
- Exemplo de página Admin (cadastro de Gestores)

Diga qual parte quer primeiro ou “gere o boilerplate completo” que eu mando os arquivos um a um. Vamos deixar isso excelente e escalável! 🚀