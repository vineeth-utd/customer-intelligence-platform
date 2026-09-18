"""product operational schema alignment

Revision ID: 6cbc003eeb50
Revises: 8d3a1b2c4e5f
Create Date: 2026-09-18 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6cbc003eeb50'
down_revision: Union[str, Sequence[str], None] = '8d3a1b2c4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('products', sa.Column('vendor', sa.String(), nullable=True))
    op.add_column('product_variants', sa.Column('size', sa.String(), nullable=True))
    op.add_column('product_variants', sa.Column('color', sa.String(), nullable=True))
    op.drop_column('product_variants', 'currency')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('product_variants', sa.Column('currency', sa.String(), nullable=False, server_default='USD'))
    op.drop_column('product_variants', 'color')
    op.drop_column('product_variants', 'size')
    op.drop_column('products', 'vendor')
