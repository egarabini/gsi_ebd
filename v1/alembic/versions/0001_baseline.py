"""Baseline da v1: o schema nasce dos modelos, nao das revisoes da v0.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-20
"""
import gsi_ebd.models  # noqa: F401
from sqlmodel import SQLModel

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    SQLModel.metadata.create_all(op_bind())


def downgrade() -> None:
    raise RuntimeError("o baseline da v1 nao tem downgrade")


def op_bind():
    from alembic import op

    return op.get_bind()
