"""merchant plan and feature natural keys

Revision ID: c62221fbbf2f
Revises: a1770327f2ef
Create Date: 2026-09-17 17:23:11.545084

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c62221fbbf2f'
down_revision: Union[str, Sequence[str], None] = 'a1770327f2ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('platform_features', sa.Column('feature_key', sa.String(), nullable=False))
    op.create_unique_constraint('uq_platform_features_feature_key', 'platform_features', ['feature_key'])
    op.add_column('subscription_plans', sa.Column('plan_key', sa.String(), nullable=False))
    op.create_unique_constraint('uq_subscription_plans_plan_key', 'subscription_plans', ['plan_key'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_subscription_plans_plan_key', 'subscription_plans', type_='unique')
    op.drop_column('subscription_plans', 'plan_key')
    op.drop_constraint('uq_platform_features_feature_key', 'platform_features', type_='unique')
    op.drop_column('platform_features', 'feature_key')
