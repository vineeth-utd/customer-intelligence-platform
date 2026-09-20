from collections.abc import Awaitable, Callable
from time import timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.campaign import (
    create_campaign,
    get_campaign,
    is_order_attributed_to_campaign,
    update_campaign_fields,
    upsert_campaign_analytics_daily,
)
from app.data_access.merchant import get_merchant_by_id
from app.data_access.order import get_order
from app.data_access.segment import get_merchant_segments
from app.schemas.events.envelope import CampaignEventEnvelope
from app.schemas.events.event_types import CampaignEventType
from app.schemas.events.payloads.campaign import (
    CampaignCreatedPayload,
    CampaignUpdatedPayload,
    CampaignConvertedPayload,
)

_SUPPORTED_UPDATED_FIELDS = {"campaign_name", "segment_id", "status", "start_at", "end_at"}

class UnresolvedReferenceError(RuntimeError):
    pass

class UnsupportedConfigurationFieldError(ValueError):
    pass

class AttributionError(ValueError):
    pass


async def _handle_campaign_created(session: AsyncSession, envelope: CampaignEventEnvelope) -> None:
    payload = CampaignCreatedPayload.model_validate(envelope.payload)
    merchant = await get_merchant_by_id(session, envelope.merchant_id)
    if merchant is None:
        raise UnresolvedReferenceError(f"Merchant {envelope.merchant_id} not found")

    segments = await get_merchant_segments(session, envelope.merchant_id)
    if payload.segment_id not in [s.segment_id for s in segments]:
        raise UnresolvedReferenceError(f"Segment {payload.segment_id} not found for Merchant {envelope.merchant_id}")

    await create_campaign(
        session,
        campaign_id=envelope.campaign_id,
        merchant_id=envelope.merchant_id,
        segment_id=payload.segment_id,
        campaign_name=payload.campaign_name,
        campaign_type=payload.campaign_type,
        campaign_medium=payload.campaign_medium,
        status=payload.status,
        start_at=payload.start_at,
        end_at=payload.end_at,
    )


async def _handle_campaign_updated(session: AsyncSession, envelope: CampaignEventEnvelope) -> None:
    payload = CampaignUpdatedPayload.model_validate(envelope.payload)
    unsupported = set(payload.changed_values) - _SUPPORTED_UPDATED_FIELDS
    if unsupported:
        raise UnsupportedConfigurationFieldError(f"Unsupported campaign fields: {sorted(unsupported)}")

    campaign = await get_campaign(session, envelope.campaign_id)
    if campaign is None:
        raise UnresolvedReferenceError(f"Campaign {envelope.campaign_id} not found")

    if "segment_id" in payload.changed_values:
        segments = await get_merchant_segments(session, campaign.merchant_id)
        # convert the string back to UUID since payload values are JSON
        import uuid
        segment_id = uuid.UUID(payload.changed_values["segment_id"]) if isinstance(payload.changed_values["segment_id"], str) else payload.changed_values["segment_id"]
        if segment_id not in [s.segment_id for s in segments]:
            raise UnresolvedReferenceError(f"Segment {segment_id} not found for Merchant {campaign.merchant_id}")
        payload.changed_values["segment_id"] = segment_id

    update_campaign_fields(campaign, payload.changed_values)


async def _handle_delivered(session: AsyncSession, envelope: CampaignEventEnvelope) -> None:
    await upsert_campaign_analytics_daily(
        session,
        campaign_id=envelope.campaign_id,
        metric_date=envelope.event_timestamp.astimezone(timezone.utc).date(),
        delivered_inc=1
    )


async def _handle_opened(session: AsyncSession, envelope: CampaignEventEnvelope) -> None:
    await upsert_campaign_analytics_daily(
        session,
        campaign_id=envelope.campaign_id,
        metric_date=envelope.event_timestamp.astimezone(timezone.utc).date(),
        opened_inc=1
    )


async def _handle_clicked(session: AsyncSession, envelope: CampaignEventEnvelope) -> None:
    await upsert_campaign_analytics_daily(
        session,
        campaign_id=envelope.campaign_id,
        metric_date=envelope.event_timestamp.astimezone(timezone.utc).date(),
        clicked_inc=1
    )


async def _handle_campaign_converted(session: AsyncSession, envelope: CampaignEventEnvelope) -> None:
    payload = CampaignConvertedPayload.model_validate(envelope.payload)
    campaign = await get_campaign(session, envelope.campaign_id)
    if campaign is None:
        raise UnresolvedReferenceError(f"Campaign {envelope.campaign_id} not found")

    if campaign.start_at is None:
        raise AttributionError(f"Cannot attribute conversion: Campaign {campaign.campaign_id} has not started")

    order = await get_order(session, payload.order_id)
    if order is None:
        raise UnresolvedReferenceError(f"Order {payload.order_id} not found")

    if order.merchant_id != campaign.merchant_id:
        raise AttributionError("Order does not belong to the campaign's merchant")

    if order.placed_at < campaign.start_at:
        raise AttributionError("Order placed before campaign start")

    if envelope.shopper_id is not None and order.shopper_id != envelope.shopper_id:
        raise AttributionError("Order shopper does not match event shopper")

    is_already_attributed = await is_order_attributed_to_campaign(session, campaign.campaign_id, payload.order_id)
    if is_already_attributed:
        # User requirement 2: Treat duplicate conversion attribution as an idempotent successful no-op
        return

    await upsert_campaign_analytics_daily(
        session,
        campaign_id=envelope.campaign_id,
        metric_date=envelope.event_timestamp.astimezone(timezone.utc).date(),
        converted_inc=1,
        order_inc=1,
        revenue_inc=float(order.total_amount)
    )


_HANDLERS: dict[CampaignEventType, Callable[[AsyncSession, CampaignEventEnvelope], Awaitable[None]]] = {
    CampaignEventType.CAMPAIGN_CREATED: _handle_campaign_created,
    CampaignEventType.CAMPAIGN_UPDATED: _handle_campaign_updated,
    CampaignEventType.EMAIL_DELIVERED: _handle_delivered,
    CampaignEventType.EMAIL_OPENED: _handle_opened,
    CampaignEventType.EMAIL_CLICKED: _handle_clicked,
    CampaignEventType.SMS_DELIVERED: _handle_delivered,
    CampaignEventType.SMS_CLICKED: _handle_clicked,
    CampaignEventType.PUSH_DELIVERED: _handle_delivered,
    CampaignEventType.PUSH_OPENED: _handle_opened,
    CampaignEventType.AD_VIEWED: _handle_delivered,
    CampaignEventType.AD_CLICKED: _handle_clicked,
    CampaignEventType.CAMPAIGN_CONVERTED: _handle_campaign_converted,
}


async def process_campaign_event(session: AsyncSession, envelope: CampaignEventEnvelope) -> None:
    handler = _HANDLERS[envelope.event_type]
    await handler(session, envelope)
