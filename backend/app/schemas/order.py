from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    order_id: UUID
    merchant_id: UUID
    shopper_id: UUID
    order_status: str
    currency: str
    total_amount: float
    placed_at: datetime
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
