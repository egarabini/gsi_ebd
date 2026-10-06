"""equipes, ambientes e hierarquia de 4 papeis

Cria o que a visao do produto exige:

- ambiente / ambienteestudo : o tenant de cada Coordenador e os estudos do
  catalogo que ele ESCOLHEU usar (o catalogo e mantido pelo Administrador).
- equipe / equipeinstrutor  : a EQUIPE entre o Coordenador e o Instrutor,
  usada para separar os instrutores por nivel de estudo.
- user: coordenador_id, instrutor_id, equipe_id, ambiente_id
  (remove gestor_id, que nao existe no produto)
- turma: ambiente_id, equipe_id, instrutor_id

Revision ID: b2a3c4d5e6f7
Revises: a1f2c3d4e5b6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


revision: str = 'b2a3c4d5e6f7'
down_revision: Union[str, None] = 'a1f2c3d4e5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NC = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
}


def upgrade() -> None:
    # ── ambiente (tenant do Coordenador) ────────────────────────────────────
    op.create_table(
        'ambiente',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('slug', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('coordenador_id', sa.Integer(), nullable=False),
        sa.Column('logo_url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('cor_primaria', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('cor_secundaria', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('tipografia', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('landing_titulo', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('landing_subtitulo', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('landing_ativa', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['coordenador_id'], ['user.id'],
                                name='fk_ambiente_coordenador_id_user'),
        sa.PrimaryKeyConstraint('id', name='pk_ambiente'),
    )
    op.create_index('ix_ambiente_slug', 'ambiente', ['slug'])
    op.create_index('ix_ambiente_coordenador_id', 'ambiente', ['coordenador_id'])

    # ── ambienteestudo (estudo do catalogo escolhido pelo ambiente) ─────────
    op.create_table(
        'ambienteestudo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ambiente_id', sa.Integer(), nullable=False),
        sa.Column('study_id', sa.Integer(), nullable=False),
        sa.Column('escolhido_por', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ambiente_id'], ['ambiente.id'],
                                name='fk_ambienteestudo_ambiente_id_ambiente'),
        sa.ForeignKeyConstraint(['study_id'], ['study.id'],
                                name='fk_ambienteestudo_study_id_study'),
        sa.ForeignKeyConstraint(['escolhido_por'], ['user.id'],
                                name='fk_ambienteestudo_escolhido_por_user'),
        sa.PrimaryKeyConstraint('id', name='pk_ambienteestudo'),
    )
    op.create_index('ix_ambienteestudo_ambiente_id', 'ambienteestudo', ['ambiente_id'])
    op.create_index('ix_ambienteestudo_study_id', 'ambienteestudo', ['study_id'])

    # ── equipe (entre Coordenador e Instrutor, por nivel) ───────────────────
    op.create_table(
        'equipe',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('descricao', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('ambiente_id', sa.Integer(), nullable=True),
        sa.Column('coordenador_id', sa.Integer(), nullable=True),
        sa.Column('nivel', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ambiente_id'], ['ambiente.id'],
                                name='fk_equipe_ambiente_id_ambiente'),
        sa.ForeignKeyConstraint(['coordenador_id'], ['user.id'],
                                name='fk_equipe_coordenador_id_user'),
        sa.PrimaryKeyConstraint('id', name='pk_equipe'),
    )
    op.create_index('ix_equipe_ambiente_id', 'equipe', ['ambiente_id'])
    op.create_index('ix_equipe_coordenador_id', 'equipe', ['coordenador_id'])

    # ── equipeinstrutor ─────────────────────────────────────────────────────
    op.create_table(
        'equipeinstrutor',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('equipe_id', sa.Integer(), nullable=False),
        sa.Column('instrutor_id', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['equipe_id'], ['equipe.id'],
                                name='fk_equipeinstrutor_equipe_id_equipe'),
        sa.ForeignKeyConstraint(['instrutor_id'], ['user.id'],
                                name='fk_equipeinstrutor_instrutor_id_user'),
        sa.PrimaryKeyConstraint('id', name='pk_equipeinstrutor'),
    )
    op.create_index('ix_equipeinstrutor_equipe_id', 'equipeinstrutor', ['equipe_id'])
    op.create_index('ix_equipeinstrutor_instrutor_id', 'equipeinstrutor', ['instrutor_id'])

    # ── user: vinculos da nova hierarquia ──────────────────────────────────
    with op.batch_alter_table('user', schema=None, naming_convention=NC) as b:
        b.add_column(sa.Column('instrutor_id', sa.Integer(), nullable=True))
        b.add_column(sa.Column('equipe_id', sa.Integer(), nullable=True))
        b.add_column(sa.Column('ambiente_id', sa.Integer(), nullable=True))
        b.create_foreign_key('fk_user_instrutor_id_user', 'user', ['instrutor_id'], ['id'])
        b.create_foreign_key('fk_user_equipe_id_equipe', 'equipe', ['equipe_id'], ['id'])
        b.create_foreign_key('fk_user_ambiente_id_ambiente', 'ambiente', ['ambiente_id'], ['id'])
        b.create_index('ix_user_ambiente_id', ['ambiente_id'])
        b.create_index('ix_user_equipe_id', ['equipe_id'])
        # gestor_id nao existe na hierarquia do produto
        try:
            b.drop_column('gestor_id')
        except Exception:
            pass

    # ── turma: ambiente + equipe + instrutor ───────────────────────────────
    with op.batch_alter_table('turma', schema=None, naming_convention=NC) as b:
        b.add_column(sa.Column('ambiente_id', sa.Integer(), nullable=True))
        b.add_column(sa.Column('equipe_id', sa.Integer(), nullable=True))
        b.add_column(sa.Column('instrutor_id', sa.Integer(), nullable=True))
        b.create_foreign_key('fk_turma_ambiente_id_ambiente', 'ambiente', ['ambiente_id'], ['id'])
        b.create_foreign_key('fk_turma_equipe_id_equipe', 'equipe', ['equipe_id'], ['id'])
        b.create_index('ix_turma_ambiente_id', ['ambiente_id'])
        b.create_index('ix_turma_equipe_id', ['equipe_id'])


def downgrade() -> None:
    with op.batch_alter_table('turma', schema=None, naming_convention=NC) as b:
        b.drop_index('ix_turma_equipe_id')
        b.drop_index('ix_turma_ambiente_id')
        b.drop_constraint('fk_turma_equipe_id_equipe', type_='foreignkey')
        b.drop_constraint('fk_turma_ambiente_id_ambiente', type_='foreignkey')
        b.drop_column('instrutor_id')
        b.drop_column('equipe_id')
        b.drop_column('ambiente_id')

    with op.batch_alter_table('user', schema=None, naming_convention=NC) as b:
        b.drop_index('ix_user_equipe_id')
        b.drop_index('ix_user_ambiente_id')
        b.drop_constraint('fk_user_ambiente_id_ambiente', type_='foreignkey')
        b.drop_constraint('fk_user_equipe_id_equipe', type_='foreignkey')
        b.drop_constraint('fk_user_instrutor_id_user', type_='foreignkey')
        b.drop_column('ambiente_id')
        b.drop_column('equipe_id')
        b.drop_column('instrutor_id')
        b.add_column(sa.Column('gestor_id', sa.Integer(), nullable=True))

    op.drop_index('ix_equipeinstrutor_instrutor_id', 'equipeinstrutor')
    op.drop_index('ix_equipeinstrutor_equipe_id', 'equipeinstrutor')
    op.drop_table('equipeinstrutor')
    op.drop_index('ix_equipe_coordenador_id', 'equipe')
    op.drop_index('ix_equipe_ambiente_id', 'equipe')
    op.drop_table('equipe')
    op.drop_index('ix_ambienteestudo_study_id', 'ambienteestudo')
    op.drop_index('ix_ambienteestudo_ambiente_id', 'ambienteestudo')
    op.drop_table('ambienteestudo')
    op.drop_index('ix_ambiente_coordenador_id', 'ambiente')
    op.drop_index('ix_ambiente_slug', 'ambiente')
    op.drop_table('ambiente')
