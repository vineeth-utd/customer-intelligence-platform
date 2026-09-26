from datetime import datetime
from typing import Optional
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
