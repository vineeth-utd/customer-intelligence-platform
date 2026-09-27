import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.event import CampaignEvent
from app.schemas.events.event_types import CampaignEventType


async def create_campaign(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    merchant_id: uuid.UUID,
    segment_id: uuid.UUID,
    campaign_name: str,
    campaign_type: str,
    campaign_medium: str,
    status: str,
    start_at: Any | None = None,
    end_at: Any | None = None,
) -> Campaign:
    campaign = Campaign(
        campaign_id=campaign_id,
        merchant_id=merchant_id,
        segment_id=segment_id,
        campaign_name=campaign_name,
        campaign_type=campaign_type,
        campaign_medium=campaign_medium,
        status=status,
        start_at=start_at,
        end_at=end_at,
    )
    session.add(campaign)
    return campaign


async def get_campaign(session: AsyncSession, campaign_id: uuid.UUID) -> Campaign | None:
    stmt = select(Campaign).where(Campaign.campaign_id == campaign_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def update_campaign_fields(campaign: Campaign, changed_values: dict[str, Any]) -> None:
    for key, value in changed_values.items():
        if hasattr(campaign, key):
            setattr(campaign, key, value)





async def is_order_attributed_to_campaign(session: AsyncSession, campaign_id: uuid.UUID, order_id: uuid.UUID) -> bool:
    stmt = select(CampaignEvent).where(
        CampaignEvent.campaign_id == campaign_id,
        CampaignEvent.event_type == CampaignEventType.CAMPAIGN_CONVERTED.value,
        CampaignEvent.processed == True,
        CampaignEvent.payload["order_id"].astext == str(order_id),
    ).limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None
