"""trocas: status/type string, approved_by, lead days

Revision ID: f503dac74ff1
Revises: 0c484ca43e6f
Create Date: 2026-06-18 16:12:03.576931

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f503dac74ff1'
down_revision: Union[str, None] = '0c484ca43e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Antecedência mínima de troca (config global)
    op.add_column("balance_configs", sa.Column("exchange_min_lead_days", sa.Integer(), nullable=False, server_default="3"))

    # Aprovação do gestor
    op.add_column("exchanges", sa.Column("approved_by_id", sa.String(length=36), nullable=True))
    op.create_foreign_key("fk_exchanges_approved_by", "exchanges", "users", ["approved_by_id"], ["id"])

    # status/type: enum -> varchar (evita ENUM rígido no Postgres)
    op.alter_column("exchanges", "status", type_=sa.String(length=20),
                    existing_nullable=False, postgresql_using="status::text")
    op.alter_column("exchanges", "type", type_=sa.String(length=20),
                    existing_nullable=False, postgresql_using="type::text")

    # Remove os tipos ENUM antigos, agora sem uso
    op.execute("DROP TYPE IF EXISTS exchangestatus")
    op.execute("DROP TYPE IF EXISTS exchangetype")


def downgrade() -> None:
    op.drop_constraint("fk_exchanges_approved_by", "exchanges", type_="foreignkey")
    op.drop_column("exchanges", "approved_by_id")
    op.drop_column("balance_configs", "exchange_min_lead_days")
    # status/type permanecem como varchar (downgrade não recria os ENUMs)
