from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ShopperResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    shopper_id: UUID
    merchant_id: UUID
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    timezone: Optional[str] = None
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None


class ShopperProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    shopper_id: UUID
    total_orders: int
    total_spend: float
    average_order_value: float
    customer_lifetime_value: Optional[float] = None
    purchase_frequency: Optional[float] = None
    wishlist_item_count: int
    save_for_later_item_count: int
    cart_abandonment_count: Optional[int] = None
    campaign_engagement_count: int
    preferred_category: Optional[str] = None
    preferred_size: Optional[str] = None
    last_purchase_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    lifecycle_stage: Optional[str] = None
    generated_at: datetime


class ShopperJourneyEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    journey_event_id: UUID
    source_event_category: str
    source_event_id: UUID
    event_type: str
    event_timestamp: datetime
    sequence_number: int


class ShopperJourneyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    journey_id: UUID
    merchant_id: UUID
    shopper_id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    journey_status: str
    converted: bool
    order_id: Optional[UUID] = None
    entry_source: Optional[str] = None
    generated_at: datetime


class ShopperJourneyDetailResponse(ShopperJourneyResponse):
    events: List[ShopperJourneyEventResponse] = []


class ShopperSegmentMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    segment_id: UUID
    segment_name: str
    generated_at: datetime


class ShopperActivityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: UUID
    session_id: UUID
    event_type: str
    event_timestamp: datetime
    source: str
    activity_details: dict[str, Any]
