"""add store_currency to merchants

Revision ID: 8d3a1b2c4e5f
Revises: 38c150bca227
Create Date: 2026-09-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d3a1b2c4e5f'
down_revision: Union[str, Sequence[str], None] = '38c150bca227'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('merchants', sa.Column('store_currency', sa.String(), server_default='USD', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('merchants', 'store_currency')

