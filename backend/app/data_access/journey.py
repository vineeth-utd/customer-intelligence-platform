import uuid
from typing import Any

from sqlalchemy import delete, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.merchant_journey import (
    delete_merchant_journeys,
    get_qualifying_events_for_merchant,
)
from app.models.event import CampaignEvent, ShopperEvent
from app.models.journey import ShopperJourney, ShopperJourneyEvent
from app.schemas.events.event_types import CampaignEventType, ShopperEventType


async def get_qualifying_events_for_shopper(
    session: AsyncSession, shopper_id: uuid.UUID
) -> list[tuple[str, uuid.UUID, uuid.UUID, str, Any, dict[str, Any]]]:
    """
    Returns a unified, chronologically sorted list of qualifying shopper and campaign
    events for a given shopper_id.

    Returns rows with: (source_event_category, source_event_id, merchant_id, event_type, event_timestamp, payload)
    """
    shopper_stmt = select(
        literal("shopper").label("source_event_category"),
        ShopperEvent.event_id.label("source_event_id"),
        ShopperEvent.merchant_id,
        ShopperEvent.event_type,
        ShopperEvent.event_timestamp,
        ShopperEvent.payload,
    ).where(
        ShopperEvent.shopper_id == shopper_id,
        ShopperEvent.event_type.in_(
            [
                ShopperEventType.SESSION_STARTED.value,
                ShopperEventType.SESSION_ENDED.value,
                ShopperEventType.PRODUCT_VIEWED.value,
                ShopperEventType.PRODUCT_SEARCHED.value,
                ShopperEventType.WISHLIST_ADDED.value,
                ShopperEventType.WISHLIST_REMOVED.value,
                ShopperEventType.SAVE_FOR_LATER_ADDED.value,
                ShopperEventType.SAVE_FOR_LATER_REMOVED.value,
                ShopperEventType.ADD_TO_CART.value,
                ShopperEventType.REMOVE_FROM_CART.value,
                ShopperEventType.CHECKOUT_STARTED.value,
                ShopperEventType.PURCHASE_COMPLETED.value,
                ShopperEventType.RECOMMENDATION_VIEWED.value,
                ShopperEventType.RECOMMENDATION_CLICKED.value,
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
        CampaignEvent.shopper_id == shopper_id,
        CampaignEvent.event_type.in_(
            [
                CampaignEventType.EMAIL_OPENED.value,
                CampaignEventType.EMAIL_CLICKED.value,
                CampaignEventType.SMS_CLICKED.value,
                CampaignEventType.PUSH_OPENED.value,
                CampaignEventType.AD_CLICKED.value,
            ]
        ),
    )

    union_stmt = shopper_stmt.union_all(campaign_stmt).order_by("event_timestamp")
    result = await session.execute(union_stmt)
    return list(result.all())


async def delete_shopper_journeys(session: AsyncSession, shopper_id: uuid.UUID) -> None:
    """
    Deterministically delete all existing shopper journeys and their events for a given shopper.
    """
    stmt = select(ShopperJourney.journey_id).where(ShopperJourney.shopper_id == shopper_id)
    journey_ids_result = await session.execute(stmt)
    journey_ids = journey_ids_result.scalars().all()

    if journey_ids:
        await session.execute(
            delete(ShopperJourneyEvent).where(ShopperJourneyEvent.journey_id.in_(journey_ids))
        )
        await session.execute(
            delete(ShopperJourney).where(ShopperJourney.shopper_id == shopper_id)
        )
