from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"


class CampaignSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    campaign_id: UUID
    merchant_id: UUID
    segment_id: UUID
    campaign_name: str
    campaign_type: str
    campaign_medium: str
    status: str
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class CampaignDetailResponse(CampaignSummaryResponse):
    target_segment_name: Optional[str] = None

