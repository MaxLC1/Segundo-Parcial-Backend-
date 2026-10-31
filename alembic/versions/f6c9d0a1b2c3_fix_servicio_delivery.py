"""Fix servicio_delivery

Revision ID: f6c9d0a1b2c3
Revises: e5b98f24458f
Create Date: 2026-09-19 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6c9d0a1b2c3'
down_revision: Union[str, Sequence[str], None] = 'e5b98f24458f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add venta_id column
    op.add_column('servicio_delivery', sa.Column('venta_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'servicio_delivery', 'ventas', ['venta_id'], ['id'])
    
    # Alter devolucion_id to be nullable
    op.alter_column('servicio_delivery', 'devolucion_id', existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column('servicio_delivery', 'devolucion_id', existing_type=sa.Integer(), nullable=False)
    op.drop_constraint(None, 'servicio_delivery', type_='foreignkey')
    op.drop_column('servicio_delivery', 'venta_id')
