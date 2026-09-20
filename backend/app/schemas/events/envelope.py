from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, field_validator

from app.schemas.events.event_types import (
    CampaignEventType,
    MerchantEventType,
    PlatformEventType,
    ProductEventType,
    ShopperEventType,
)


class BaseEventEnvelope(BaseModel):
    """Common wire contract shared by all event families.

    Mirrors the shared columns of the SQLAlchemy event tables in
    app/models/event.py, minus processing-state columns (processed,
    processed_at, created_at), which are owned by the consumer/persistence
    layer rather than the producer's contract.
    """

    event_id: UUID
    event_version: int
    event_timestamp: datetime
    payload: dict[str, Any]
    source: str

    @field_validator("event_timestamp")
    @classmethod
    def _require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("event_timestamp must be timezone-aware")
        return value


class MerchantEventEnvelope(BaseEventEnvelope):
    event_type: MerchantEventType
    merchant_id: UUID


class ProductEventEnvelope(BaseEventEnvelope):
    event_type: ProductEventType
    merchant_id: UUID
    product_id: UUID


class ShopperEventEnvelope(BaseEventEnvelope):
    event_type: ShopperEventType
    merchant_id: UUID
    shopper_id: UUID
    session_id: UUID


class CampaignEventEnvelope(BaseEventEnvelope):
    event_type: CampaignEventType
    campaign_id: UUID
    merchant_id: UUID
    shopper_id: UUID


class PlatformEventEnvelope(BaseEventEnvelope):
    """Not published to Kafka in Version 1 (docs/11_Database_Design.md): Platform
    Events are written directly by internal backend processes. Defined here only
    for contract symmetry with the other event families.
    """

    event_type: PlatformEventType
