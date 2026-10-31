"""Add delivery info to ventas

Revision ID: 3a2b1c4d5e6f
Revises: f6c9d0a1b2c3
Create Date: 2026-09-19 22:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a2b1c4d5e6f'
down_revision: Union[str, Sequence[str], None] = 'f6c9d0a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ventas', sa.Column('tipo_entrega', sa.String(length=50), nullable=True, server_default='Recojo en Tienda'))
    op.add_column('ventas', sa.Column('direccion_envio', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('ventas', 'direccion_envio')
    op.drop_column('ventas', 'tipo_entrega')
