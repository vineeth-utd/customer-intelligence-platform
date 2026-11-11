import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.event import CampaignEvent
from app.models.shopper import ShopperSegment
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
    created_at: datetime | None = None,
) -> Campaign:
    kwargs: dict[str, Any] = {
        "campaign_id": campaign_id,
        "merchant_id": merchant_id,
        "segment_id": segment_id,
        "campaign_name": campaign_name,
        "campaign_type": campaign_type,
        "campaign_medium": campaign_medium,
        "status": status,
        "start_at": start_at,
        "end_at": end_at,
    }
    if created_at is not None:
        kwargs["created_at"] = created_at

    campaign = Campaign(**kwargs)
    session.add(campaign)
    return campaign


async def get_campaign(session: AsyncSession, campaign_id: uuid.UUID) -> Campaign | None:
    stmt = select(Campaign).where(Campaign.campaign_id == campaign_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_campaign_for_merchant(
    session: AsyncSession, merchant_id: uuid.UUID, campaign_id: uuid.UUID
) -> Campaign | None:
    stmt = select(Campaign).where(
        Campaign.merchant_id == merchant_id,
        Campaign.campaign_id == campaign_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_campaign_detail_with_segment(
    session: AsyncSession, merchant_id: uuid.UUID, campaign_id: uuid.UUID
) -> tuple[Campaign, Optional[str]] | None:
    stmt = (
        select(Campaign, ShopperSegment.segment_name)
        .outerjoin(ShopperSegment, ShopperSegment.segment_id == Campaign.segment_id)
        .where(
            Campaign.merchant_id == merchant_id,
            Campaign.campaign_id == campaign_id,
        )
    )
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        return None
    return row[0], row[1]


async def list_merchant_campaigns(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
) -> tuple[list[Campaign], int]:
    base_filter = [Campaign.merchant_id == merchant_id]
    if status is not None:
        base_filter.append(Campaign.status == status)

    count_stmt = select(func.count(Campaign.campaign_id)).where(*base_filter)
    total = (await session.execute(count_stmt)).scalar() or 0

    items_stmt = (
        select(Campaign)
        .where(*base_filter)
        .order_by(Campaign.created_at.desc(), Campaign.campaign_id.desc())
        .limit(limit)
        .offset(offset)
    )
    items = (await session.execute(items_stmt)).scalars().all()
    return list(items), total


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




