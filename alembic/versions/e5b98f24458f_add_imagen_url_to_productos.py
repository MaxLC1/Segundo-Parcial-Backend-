"""Add imagen_url to Productos

Revision ID: e5b98f24458f
Revises: db46799b8c05
Create Date: 2026-09-19 21:07:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5b98f24458f'
down_revision: Union[str, Sequence[str], None] = '6c894ce26b8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('productos', sa.Column('imagen_url', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('productos', 'imagen_url')
