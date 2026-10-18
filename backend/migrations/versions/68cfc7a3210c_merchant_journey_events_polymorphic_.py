"""merchant_journey_events_polymorphic_source_lineage

Revision ID: 68cfc7a3210c
Revises: 78ebeeb7d413
Create Date: 2026-10-17 21:49:24.297129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68cfc7a3210c'
down_revision: Union[str, Sequence[str], None] = '78ebeeb7d413'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('merchant_journey_events', sa.Column('source_event_category', sa.String(), nullable=False, server_default='merchant'))
    op.alter_column('merchant_journey_events', 'source_event_category', server_default=None)
    op.drop_constraint('merchant_journey_events_source_event_id_fkey', 'merchant_journey_events', type_='foreignkey')
    op.create_unique_constraint('uq_merchant_journey_source_event', 'merchant_journey_events', ['source_event_category', 'source_event_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_merchant_journey_source_event', 'merchant_journey_events', type_='unique')
    op.create_foreign_key('merchant_journey_events_source_event_id_fkey', 'merchant_journey_events', 'merchant_events', ['source_event_id'], ['event_id'])
    op.drop_column('merchant_journey_events', 'source_event_category')
