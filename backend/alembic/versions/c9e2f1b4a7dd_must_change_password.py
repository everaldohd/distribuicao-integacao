"""users.must_change_password — troca de senha obrigatória no 1º login

Todos os usuários existentes recebem True (serão forçados a trocar a senha na
próxima entrada — decisão da fase de testes). Usuários criados via SSO nunca
usam senha local e são criados com False pela aplicação.

Revision ID: c9e2f1b4a7dd
Revises: b7d1e0a9c3aa
Create Date: 2026-07-15

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9e2f1b4a7dd"
down_revision: Union[str, None] = "b7d1e0a9c3aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
