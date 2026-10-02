from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.campaign import (
    create_campaign,
    get_campaign,
    is_order_attributed_to_campaign,
    update_campaign_fields,
    update_campaign_business_activity,
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

    # Normalize and validate changed_values
    for field in ["start_at", "end_at"]:
        if field in payload.changed_values:
            val = payload.changed_values[field]
            if val is not None:
                if isinstance(val, str):
                    try:
                        val_dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                        if val_dt.tzinfo is None:
                            val_dt = val_dt.replace(tzinfo=UTC)
                        payload.changed_values[field] = val_dt
                    except ValueError as e:
                        raise UnsupportedConfigurationFieldError(f"Invalid datetime format for {field}: {e}")
                elif isinstance(val, datetime):
                    if val.tzinfo is None:
                        val = val.replace(tzinfo=UTC)
                    payload.changed_values[field] = val
                else:
                    raise UnsupportedConfigurationFieldError(f"Invalid type for {field}")

    if "segment_id" in payload.changed_values:
        val = payload.changed_values["segment_id"]
        if val is None:
            raise UnsupportedConfigurationFieldError("segment_id cannot be None")
        if isinstance(val, str):
            try:
                payload.changed_values["segment_id"] = uuid.UUID(val)
            except ValueError as e:
                raise UnsupportedConfigurationFieldError(f"Invalid UUID for segment_id: {e}")
        elif not isinstance(val, uuid.UUID):
            raise UnsupportedConfigurationFieldError("Invalid type for segment_id")

    for string_field in ["campaign_name", "status"]:
        if string_field in payload.changed_values:
            val = payload.changed_values[string_field]
            if val is None:
                raise UnsupportedConfigurationFieldError(f"{string_field} cannot be None")
            if not isinstance(val, str):
                raise UnsupportedConfigurationFieldError(f"Invalid type for {string_field}")

    campaign = await get_campaign(session, envelope.campaign_id)
    if campaign is None:
        raise UnresolvedReferenceError(f"Campaign {envelope.campaign_id} not found")

    if "segment_id" in payload.changed_values:
        segment_id = payload.changed_values["segment_id"]
        segments = await get_merchant_segments(session, campaign.merchant_id)
        if segment_id not in [s.segment_id for s in segments]:
            raise UnresolvedReferenceError(f"Segment {segment_id} not found for Merchant {campaign.merchant_id}")

    update_campaign_fields(campaign, payload.changed_values)


async def _handle_delivered(session: AsyncSession, envelope: CampaignEventEnvelope) -> None:
    pass  # Intentional no-op; handled asynchronously by the analytics service


async def _handle_opened(session: AsyncSession, envelope: CampaignEventEnvelope) -> None:
    pass  # Intentional no-op; handled asynchronously by the analytics service


async def _handle_clicked(session: AsyncSession, envelope: CampaignEventEnvelope) -> None:
    pass  # Intentional no-op; handled asynchronously by the analytics service


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
    await update_campaign_business_activity(session, envelope.campaign_id, envelope.event_timestamp)
