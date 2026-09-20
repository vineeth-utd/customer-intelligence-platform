import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.event import CampaignEvent
from app.models.metrics import CampaignAnalyticsDaily
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


async def upsert_campaign_analytics_daily(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    metric_date: date,
    delivered_inc: int = 0,
    opened_inc: int = 0,
    clicked_inc: int = 0,
    converted_inc: int = 0,
    order_inc: int = 0,
    revenue_inc: float = 0.0,
) -> None:
    stmt = (
        pg_insert(CampaignAnalyticsDaily)
        .values(
            campaign_id=campaign_id,
            metric_date=metric_date,
            delivered_count=delivered_inc,
            opened_count=opened_inc,
            clicked_count=clicked_inc,
            converted_count=converted_inc,
            attributed_order_count=order_inc,
            attributed_revenue=revenue_inc,
            open_rate=0.0,
            click_through_rate=0.0,
            conversion_rate=0.0,
            generated_at=func.now(),
        )
        .on_conflict_do_update(
            index_elements=["campaign_id", "metric_date"],
            set_={
                "delivered_count": CampaignAnalyticsDaily.delivered_count + delivered_inc,
                "opened_count": CampaignAnalyticsDaily.opened_count + opened_inc,
                "clicked_count": CampaignAnalyticsDaily.clicked_count + clicked_inc,
                "converted_count": CampaignAnalyticsDaily.converted_count + converted_inc,
                "attributed_order_count": CampaignAnalyticsDaily.attributed_order_count + order_inc,
                "attributed_revenue": CampaignAnalyticsDaily.attributed_revenue + revenue_inc,
                "generated_at": func.now(),
            },
        )
        .returning(CampaignAnalyticsDaily)
    )
    result = await session.execute(stmt)
    updated = result.scalar_one()

    delivered = updated.delivered_count
    updated.open_rate = float(updated.opened_count) / delivered if delivered > 0 else 0.0
    updated.click_through_rate = float(updated.clicked_count) / delivered if delivered > 0 else 0.0
    updated.conversion_rate = float(updated.converted_count) / delivered if delivered > 0 else 0.0


async def is_order_attributed_to_campaign(session: AsyncSession, campaign_id: uuid.UUID, order_id: uuid.UUID) -> bool:
    stmt = select(CampaignEvent).where(
        CampaignEvent.campaign_id == campaign_id,
        CampaignEvent.event_type == CampaignEventType.CAMPAIGN_CONVERTED.value,
        CampaignEvent.processed == True,
        CampaignEvent.payload["order_id"].astext == str(order_id),
    ).limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None
