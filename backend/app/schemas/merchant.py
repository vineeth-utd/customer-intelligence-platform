from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    plan_id: UUID
    status: str
    billing_cycle: str
    amount_paid: float
    started_at: datetime
    renewal_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None


class MerchantDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    merchant_id: UUID
    merchant_name: str
    shopify_store_id: str
    email: str
    country: Optional[str] = None
    timezone: Optional[str] = None
    store_currency: str
    app_install_status: str
    last_active_at: Optional[datetime] = None
    active_subscription: Optional[SubscriptionResponse] = None


class MerchantSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    merchant_id: UUID
    merchant_name: str
    shopify_store_id: str
    email: str
    store_currency: str
    app_install_status: str
    last_active_at: Optional[datetime] = None
