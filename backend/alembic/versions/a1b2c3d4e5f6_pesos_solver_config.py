"""pesos do solver configuráveis (BalanceConfig)

Revision ID: a1b2c3d4e5f6
Revises: f503dac74ff1
Create Date: 2026-06-18

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f503dac74ff1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_WEIGHTS = [
    ("weight_gap", "100000"),
    ("weight_desired", "300"),
    ("weight_avoid", "200"),
    ("weight_balance", "10"),
    ("weight_load_equity", "50"),
]


def upgrade() -> None:
    for col, default in _WEIGHTS:
        op.add_column("balance_configs", sa.Column(col, sa.Integer(), nullable=False, server_default=default))


def downgrade() -> None:
    for col, _ in _WEIGHTS:
        op.drop_column("balance_configs", col)
