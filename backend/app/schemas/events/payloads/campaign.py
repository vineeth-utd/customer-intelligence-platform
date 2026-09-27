from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.schemas.events.event_types import CampaignEventType
from app.schemas.events.registry import register_event_payload


@register_event_payload(CampaignEventType.CAMPAIGN_CREATED.value, 1)
class CampaignCreatedPayload(BaseModel):
    campaign_name: str
    campaign_type: str
    campaign_medium: str
    segment_id: UUID
    status: str
    start_at: datetime | None = None
    end_at: datetime | None = None


@register_event_payload(CampaignEventType.CAMPAIGN_UPDATED.value, 1)
class CampaignUpdatedPayload(BaseModel):
    changed_values: dict[str, Any]


@register_event_payload(CampaignEventType.EMAIL_DELIVERED.value, 1)
class EmailDeliveredPayload(BaseModel):
    pass


@register_event_payload(CampaignEventType.EMAIL_OPENED.value, 1)
class EmailOpenedPayload(BaseModel):
    pass


@register_event_payload(CampaignEventType.EMAIL_CLICKED.value, 1)
class EmailClickedPayload(BaseModel):
    url: str


@register_event_payload(CampaignEventType.SMS_DELIVERED.value, 1)
class SmsDeliveredPayload(BaseModel):
    pass


@register_event_payload(CampaignEventType.SMS_CLICKED.value, 1)
class SmsClickedPayload(BaseModel):
    url: str


@register_event_payload(CampaignEventType.PUSH_DELIVERED.value, 1)
class PushDeliveredPayload(BaseModel):
    pass


@register_event_payload(CampaignEventType.PUSH_OPENED.value, 1)
class PushOpenedPayload(BaseModel):
    action: str | None = None


@register_event_payload(CampaignEventType.AD_VIEWED.value, 1)
class AdViewedPayload(BaseModel):
    pass


@register_event_payload(CampaignEventType.AD_CLICKED.value, 1)
class AdClickedPayload(BaseModel):
    url: str


@register_event_payload(CampaignEventType.CAMPAIGN_CONVERTED.value, 1)
class CampaignConvertedPayload(BaseModel):
    order_id: UUID
