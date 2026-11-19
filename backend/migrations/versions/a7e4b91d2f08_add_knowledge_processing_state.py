"""add_knowledge_processing_state

Revision ID: a7e4b91d2f08
Revises: 68cfc7a3210c
Create Date: 2026-11-18 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7e4b91d2f08'
down_revision: Union[str, Sequence[str], None] = '68cfc7a3210c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'knowledge_processing_states',
        sa.Column('point_id', sa.UUID(), nullable=False),
        sa.Column('knowledge_type', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=True),
        sa.Column('merchant_id', sa.UUID(), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('is_current', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('status', sa.String(), server_default='PENDING', nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('last_attempted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_watermark', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('schema_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('prompt_version', sa.String(), nullable=True),
        sa.Column('embedding_model', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['merchant_id'], ['merchants.merchant_id']),
        sa.PrimaryKeyConstraint('point_id')
    )
    op.create_index(
        'ix_knowledge_processing_states_type_status',
        'knowledge_processing_states',
        ['knowledge_type', 'status']
    )
    op.create_index(
        'ix_knowledge_processing_states_entity',
        'knowledge_processing_states',
        ['entity_type', 'entity_id']
    )
    op.create_index(
        'ix_knowledge_processing_states_merchant_id',
        'knowledge_processing_states',
        ['merchant_id']
    )
    op.create_index(
        'ix_knowledge_processing_states_current_status',
        'knowledge_processing_states',
        ['is_current', 'status']
    )


def downgrade() -> None:
    op.drop_index('ix_knowledge_processing_states_current_status', table_name='knowledge_processing_states')
    op.drop_index('ix_knowledge_processing_states_merchant_id', table_name='knowledge_processing_states')
    op.drop_index('ix_knowledge_processing_states_entity', table_name='knowledge_processing_states')
    op.drop_index('ix_knowledge_processing_states_type_status', table_name='knowledge_processing_states')
    op.drop_table('knowledge_processing_states')
