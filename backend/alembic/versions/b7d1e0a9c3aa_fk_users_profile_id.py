"""FK users.profile_id -> profiles.id (integridade referencial)

A coluna existia sem constraint: o banco aceitava usuário apontando para
perfil inexistente e a exclusão de um perfil deixava usuários órfãos.
Antes de criar a FK, limpamos eventuais órfãos (profile_id sem perfil
correspondente vira NULL — mesmo comportamento do ondelete="SET NULL").

Revision ID: b7d1e0a9c3aa
Revises: a1b2c3d4e5f6
Create Date: 2026-07-15

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7d1e0a9c3aa"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FK_NAME = "fk_users_profile_id_profiles"


def upgrade() -> None:
    # 1) Limpa órfãos existentes (não há como criar a FK com eles presentes)
    op.execute(
        sa.text(
            "UPDATE users SET profile_id = NULL "
            "WHERE profile_id IS NOT NULL "
            "AND profile_id NOT IN (SELECT id FROM profiles)"
        )
    )
    # 2) Cria a FK + índice (a coluna é usada em joins/filtros do solver)
    op.create_foreign_key(
        _FK_NAME,
        source_table="users",
        referent_table="profiles",
        local_cols=["profile_id"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_profile_id", "users", ["profile_id"])


def downgrade() -> None:
    op.drop_index("ix_users_profile_id", table_name="users")
    op.drop_constraint(_FK_NAME, "users", type_="foreignkey")
