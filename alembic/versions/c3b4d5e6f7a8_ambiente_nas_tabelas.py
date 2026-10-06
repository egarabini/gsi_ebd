"""ambiente_id nas tabelas de dados (isolamento por tenant)

Decisao de arquitetura: em vez de o codigo montar listas de ids visiveis, CADA
tabela de dados do tenant carrega a FK para o ambiente. Assim o isolamento e
estrutural (o banco sabe de quem e o registro), o DDL documenta, toda query
filtra por coluna em vez de join, e habilita Row-Level Security no futuro.

Tabelas que ja tinham: user, turma, ambienteestudo, equipe.
Adicionadas aqui: progress, userresponse, studyassignment, notification, subscription, paymenthistory.

Nullable na entrada para nao invalidar linhas existentes; o aplicativo passa a
preencher sempre.

Revision ID: c3b4d5e6f7a8
Revises: b2a3c4d5e6f7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3b4d5e6f7a8'
down_revision: Union[str, None] = 'b2a3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NC = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
}

TABELAS = 'progress', 'userresponse', 'studyassignment', 'notification', 'subscription', 'paymenthistory'


def upgrade() -> None:
    for tabela in ['progress', 'userresponse', 'studyassignment', 'notification', 'subscription', 'paymenthistory']:
        with op.batch_alter_table(tabela, schema=None, naming_convention=NC) as b:
            b.add_column(sa.Column('ambiente_id', sa.Integer(), nullable=True))
            b.create_foreign_key(f'fk_{tabela}_ambiente_id_ambiente',
                                 'ambiente', ['ambiente_id'], ['id'])
            b.create_index(f'ix_{tabela}_ambiente_id', ['ambiente_id'])


def downgrade() -> None:
    for tabela in ['progress', 'userresponse', 'studyassignment', 'notification', 'subscription', 'paymenthistory']:
        with op.batch_alter_table(tabela, schema=None, naming_convention=NC) as b:
            b.drop_index(f'ix_{tabela}_ambiente_id')
            b.drop_constraint(f'fk_{tabela}_ambiente_id_ambiente', type_='foreignkey')
            b.drop_column('ambiente_id')
