"""drop event table entity fks

Revision ID: 38c150bca227
Revises: c62221fbbf2f
Create Date: 2026-09-17 18:01:35.439570

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38c150bca227'
down_revision: Union[str, Sequence[str], None] = 'c62221fbbf2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f('campaign_events_merchant_id_fkey'), 'campaign_events', type_='foreignkey')
    op.drop_constraint(op.f('campaign_events_shopper_id_fkey'), 'campaign_events', type_='foreignkey')
    op.drop_constraint(op.f('campaign_events_campaign_id_fkey'), 'campaign_events', type_='foreignkey')
    op.drop_constraint(op.f('merchant_events_merchant_id_fkey'), 'merchant_events', type_='foreignkey')
    op.drop_constraint(op.f('shopper_events_shopper_id_fkey'), 'shopper_events', type_='foreignkey')
    op.drop_constraint(op.f('shopper_events_merchant_id_fkey'), 'shopper_events', type_='foreignkey')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_foreign_key(op.f('shopper_events_merchant_id_fkey'), 'shopper_events', 'merchants', ['merchant_id'], ['merchant_id'])
    op.create_foreign_key(op.f('shopper_events_shopper_id_fkey'), 'shopper_events', 'shoppers', ['shopper_id'], ['shopper_id'])
    op.create_foreign_key(op.f('merchant_events_merchant_id_fkey'), 'merchant_events', 'merchants', ['merchant_id'], ['merchant_id'])
    op.create_foreign_key(op.f('campaign_events_campaign_id_fkey'), 'campaign_events', 'campaigns', ['campaign_id'], ['campaign_id'])
    op.create_foreign_key(op.f('campaign_events_shopper_id_fkey'), 'campaign_events', 'shoppers', ['shopper_id'], ['shopper_id'])
    op.create_foreign_key(op.f('campaign_events_merchant_id_fkey'), 'campaign_events', 'merchants', ['merchant_id'], ['merchant_id'])
