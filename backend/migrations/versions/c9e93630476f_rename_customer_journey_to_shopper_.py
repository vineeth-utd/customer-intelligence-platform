"""rename_customer_journey_to_shopper_journey

Revision ID: c9e93630476f
Revises: 668d034f4304
Create Date: 2026-10-02 10:40:01.730413

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9e93630476f'
down_revision: Union[str, Sequence[str], None] = '668d034f4304'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table('customer_journeys', 'shopper_journeys')
    op.rename_table('customer_journey_events', 'shopper_journey_events')
    
    op.execute('ALTER TABLE shopper_journeys RENAME CONSTRAINT customer_journeys_pkey TO shopper_journeys_pkey')
    op.execute('ALTER TABLE shopper_journeys RENAME CONSTRAINT customer_journeys_merchant_id_fkey TO shopper_journeys_merchant_id_fkey')
    op.execute('ALTER TABLE shopper_journeys RENAME CONSTRAINT customer_journeys_shopper_id_fkey TO shopper_journeys_shopper_id_fkey')
    op.execute('ALTER TABLE shopper_journeys RENAME CONSTRAINT customer_journeys_order_id_fkey TO shopper_journeys_order_id_fkey')
    op.execute('ALTER TABLE shopper_journey_events RENAME CONSTRAINT customer_journey_events_pkey TO shopper_journey_events_pkey')
    op.execute('ALTER TABLE shopper_journey_events RENAME CONSTRAINT customer_journey_events_journey_id_fkey TO shopper_journey_events_journey_id_fkey')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('ALTER TABLE shopper_journey_events RENAME CONSTRAINT shopper_journey_events_journey_id_fkey TO customer_journey_events_journey_id_fkey')
    op.execute('ALTER TABLE shopper_journey_events RENAME CONSTRAINT shopper_journey_events_pkey TO customer_journey_events_pkey')
    op.execute('ALTER TABLE shopper_journeys RENAME CONSTRAINT shopper_journeys_order_id_fkey TO customer_journeys_order_id_fkey')
    op.execute('ALTER TABLE shopper_journeys RENAME CONSTRAINT shopper_journeys_shopper_id_fkey TO customer_journeys_shopper_id_fkey')
    op.execute('ALTER TABLE shopper_journeys RENAME CONSTRAINT shopper_journeys_merchant_id_fkey TO customer_journeys_merchant_id_fkey')
    op.execute('ALTER TABLE shopper_journeys RENAME CONSTRAINT shopper_journeys_pkey TO customer_journeys_pkey')
    
    op.rename_table('shopper_journey_events', 'customer_journey_events')
    op.rename_table('shopper_journeys', 'customer_journeys')
