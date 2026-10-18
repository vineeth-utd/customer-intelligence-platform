import uuid
from typing import Any

from sqlalchemy import delete, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import CampaignEvent, MerchantEvent
from app.models.journey import MerchantJourney, MerchantJourneyEvent
from app.schemas.events.event_types import CampaignEventType, MerchantEventType


async def get_qualifying_events_for_merchant(
    session: AsyncSession, merchant_id: uuid.UUID
) -> list[tuple[str, uuid.UUID, uuid.UUID, str, Any, dict[str, Any]]]:
    """
    Returns a unified, chronologically sorted list of qualifying merchant and campaign
    events for a given merchant_id.

    Returns rows with: (source_event_category, source_event_id, merchant_id, event_type, event_timestamp, payload)
    """
    merchant_stmt = select(
        literal("merchant").label("source_event_category"),
        MerchantEvent.event_id.label("source_event_id"),
        MerchantEvent.merchant_id,
        MerchantEvent.event_type,
        MerchantEvent.event_timestamp,
        MerchantEvent.payload,
    ).where(
        MerchantEvent.merchant_id == merchant_id,
        MerchantEvent.event_type.in_(
            [
                MerchantEventType.APP_INSTALLED.value,
                MerchantEventType.APP_UNINSTALLED.value,
                MerchantEventType.MERCHANT_CREATED.value,
                MerchantEventType.SUBSCRIPTION_STARTED.value,
                MerchantEventType.SUBSCRIPTION_RENEWED.value,
                MerchantEventType.SUBSCRIPTION_UPGRADED.value,
                MerchantEventType.SUBSCRIPTION_DOWNGRADED.value,
                MerchantEventType.SUBSCRIPTION_CANCELLED.value,
                MerchantEventType.FEATURE_ENABLED.value,
                MerchantEventType.FEATURE_DISABLED.value,
                MerchantEventType.MERCHANT_CONFIGURATION_UPDATED.value,
                MerchantEventType.MERCHANT_LOGIN.value,
            ]
        ),
    )

    campaign_stmt = select(
        literal("campaign").label("source_event_category"),
        CampaignEvent.event_id.label("source_event_id"),
        CampaignEvent.merchant_id,
        CampaignEvent.event_type,
        CampaignEvent.event_timestamp,
        CampaignEvent.payload,
    ).where(
        CampaignEvent.merchant_id == merchant_id,
        CampaignEvent.event_type.in_(
            [
                CampaignEventType.CAMPAIGN_CREATED.value,
                CampaignEventType.CAMPAIGN_UPDATED.value,
            ]
        ),
    )

    union_stmt = merchant_stmt.union_all(campaign_stmt).order_by("event_timestamp", "source_event_id")
    result = await session.execute(union_stmt)
    return list(result.all())


async def delete_merchant_journeys(session: AsyncSession, merchant_id: uuid.UUID) -> None:
    """
    Deterministically delete all existing merchant journeys and their events for a given merchant.
    """
    stmt = select(MerchantJourney.merchant_journey_id).where(MerchantJourney.merchant_id == merchant_id)
    journey_ids_result = await session.execute(stmt)
    journey_ids = journey_ids_result.scalars().all()

    if journey_ids:
        await session.execute(
            delete(MerchantJourneyEvent).where(MerchantJourneyEvent.merchant_journey_id.in_(journey_ids))
        )
        await session.execute(
            delete(MerchantJourney).where(MerchantJourney.merchant_id == merchant_id)
        )
