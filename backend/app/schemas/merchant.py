from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_id: UUID
    plan_name: str
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


class MerchantProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_id: UUID
    total_shoppers: int
    total_products: int
    total_orders: int
    total_revenue: float
    average_order_value: float
    conversion_rate: float
    total_campaigns: int
    active_campaign_count: int
    enabled_feature_count: int
    last_order_at: Optional[datetime] = None
    last_campaign_at: Optional[datetime] = None
    generated_at: datetime


class MerchantHealthFactorsResponse(BaseModel):
    feature_adoption: dict[str, Any]
    engagement: dict[str, Any]
    business_performance: dict[str, Any]
    subscription: dict[str, Any]
    risk_alerts: List[str]


class MerchantHealthResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_id: UUID
    health_score: float
    health_status: str
    churn_risk_score: float
    engagement_score: float
    feature_adoption_score: float
    business_performance_score: float
    calculated_at: datetime
    contributing_factors: MerchantHealthFactorsResponse


class MerchantJourneyEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_journey_event_id: UUID
    source_event_category: str
    source_event_id: UUID
    event_type: str
    event_timestamp: datetime
    sequence_number: int


class MerchantJourneyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    merchant_journey_id: UUID
    merchant_id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    journey_status: str
    generated_at: datetime


class MerchantJourneyDetailResponse(MerchantJourneyResponse):
    events: List[MerchantJourneyEventResponse] = []


class MerchantFeatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feature_id: UUID
    feature_key: str
    feature_name: str
    feature_category: str
    description: Optional[str] = None
    is_entitled: bool
    is_enabled: bool
