"""adiciona turma e turmamembro

Revision ID: 95d76c5dbb2f
Revises: b55ed43e2631
Create Date: 2026-07-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '95d76c5dbb2f'
down_revision: Union[str, Sequence[str], None] = 'b55ed43e2631'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('turma',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nome', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('descricao', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('gestor_id', sa.Integer(), nullable=False),
    sa.Column('coordenador_id', sa.Integer(), nullable=True),
    sa.Column('study_id', sa.Integer(), nullable=True),
    sa.Column('data_inicio', sa.Date(), nullable=True),
    sa.Column('data_fim', sa.Date(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['coordenador_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['gestor_id'], ['user.id'], ),
    sa.ForeignKeyConstraint(['study_id'], ['study.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('turmamembro',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('turma_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('data_entrada', sa.Date(), nullable=False),
    sa.Column('data_saida', sa.Date(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['turma_id'], ['turma.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('turmamembro')
    op.drop_table('turma')
    # ### end Alembic commands ###
