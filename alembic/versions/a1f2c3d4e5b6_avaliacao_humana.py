"""avaliacao humana das respostas abertas

Adiciona a UserResponse o que faltava para o ciclo do instrutor:
instructor_feedback (o parecer), reviewed_by (quem avaliou) e reviewed_at.

Questoes abertas passam a nascer com is_correct=None e permanecem na fila
ate um instrutor avalia-las.

Revision ID: a1f2c3d4e5b6
Revises: cf5b71f0e3bc
Create Date: 2026-10-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'a1f2c3d4e5b6'
down_revision: Union[str, None] = 'cf5b71f0e3bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('userresponse', schema=None,
                               naming_convention={
                                   "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
                                   "pk": "pk_%(table_name)s",
                                   "ix": "ix_%(table_name)s_%(column_0_name)s",
                                   "uq": "uq_%(table_name)s_%(column_0_name)s",
                               }) as batch_op:
        batch_op.add_column(sa.Column('instructor_feedback',
                                      sqlmodel.sql.sqltypes.AutoString(),
                                      server_default=sa.text("''"), nullable=False))
        batch_op.add_column(sa.Column('reviewed_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('reviewed_at', sa.DateTime(), nullable=True))
        batch_op.create_foreign_key('fk_userresponse_reviewed_by_user',
                                    'user', ['reviewed_by'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('userresponse', schema=None,
                               naming_convention={
                                   "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
                                   "pk": "pk_%(table_name)s",
                                   "ix": "ix_%(table_name)s_%(column_0_name)s",
                                   "uq": "uq_%(table_name)s_%(column_0_name)s",
                               }) as batch_op:
        batch_op.drop_constraint('fk_userresponse_reviewed_by_user', type_='foreignkey')
        batch_op.drop_column('reviewed_at')
        batch_op.drop_column('reviewed_by')
        batch_op.drop_column('instructor_feedback')
