"""product events table

Revision ID: df49fbe0e3b9
Revises: 6cbc003eeb50
Create Date: 2026-09-18 12:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'df49fbe0e3b9'
down_revision: Union[str, Sequence[str], None] = '6cbc003eeb50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('product_events',
    sa.Column('event_id', sa.UUID(), nullable=False),
    sa.Column('merchant_id', sa.UUID(), nullable=False),
    sa.Column('product_id', sa.UUID(), nullable=False),
    sa.Column('event_type', sa.String(), nullable=False),
    sa.Column('event_version', sa.Integer(), nullable=False),
    sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('source', sa.String(), nullable=False),
    sa.Column('processed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index(op.f('ix_product_events_event_type'), 'product_events', ['event_type'], unique=False)
    op.create_index('ix_product_events_merchant_id_event_timestamp', 'product_events', ['merchant_id', 'event_timestamp'], unique=False)
    op.create_index('ix_product_events_product_id_event_timestamp', 'product_events', ['product_id', 'event_timestamp'], unique=False)
    op.create_index(op.f('ix_product_events_processed'), 'product_events', ['processed'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_product_events_processed'), table_name='product_events')
    op.drop_index('ix_product_events_product_id_event_timestamp', table_name='product_events')
    op.drop_index('ix_product_events_merchant_id_event_timestamp', table_name='product_events')
    op.drop_index(op.f('ix_product_events_event_type'), table_name='product_events')
    op.drop_table('product_events')
