from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, Union
import uuid

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeType(str, Enum):
    MERCHANT_SUMMARY = "merchant_summary"
    SHOPPER_BEHAVIOUR = "shopper_behaviour"
    SHOPPER_JOURNEY = "shopper_journey"
    CAMPAIGN_SUMMARY = "campaign_summary"
    MERCHANT_PERFORMANCE = "merchant_performance"
    PLATFORM_PERFORMANCE = "platform_performance"


class KnowledgeStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class KnowledgeAccessScope(str, Enum):
    INTERNAL = "INTERNAL"
    MERCHANT = "MERCHANT"


class SourceReference(BaseModel):
    """Flexible deterministic business locator for lineage tracing."""
    model_config = ConfigDict(extra="forbid")

    source_type: str
    source_reference: Union[str, dict[str, Any]]
    as_of: Optional[datetime] = None
    description: Optional[str] = None


class KnowledgeMetadata(BaseModel):
    """Common metadata envelope for all AI knowledge items."""
    model_config = ConfigDict(extra="forbid")

    point_id: uuid.UUID
    knowledge_type: KnowledgeType
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    merchant_id: Optional[uuid.UUID] = None
    shopper_id: Optional[uuid.UUID] = None
    campaign_id: Optional[uuid.UUID] = None
    journey_id: Optional[uuid.UUID] = None
    entity_name: Optional[str] = None
    as_of: datetime
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    is_current: bool
    access_scope: KnowledgeAccessScope
    source_references: list[SourceReference] = Field(default_factory=list)
    schema_version: int = 1
    embedding_model: Optional[str] = None
    prompt_version: Optional[str] = None


class MerchantSummaryFacts(BaseModel):
    """Deterministic, AI-safe facts representing current merchant profile, health, and activity."""
    model_config = ConfigDict(extra="forbid")

    merchant_name: str
    store_currency: str
    country: str
    timezone: str
    app_install_status: str
    subscription_plan: Optional[str] = None
    total_shoppers: int
    total_products: int
    total_orders: int
    total_revenue: Decimal
    average_order_value: Decimal
    conversion_rate: Decimal
    active_campaign_count: int
    enabled_feature_count: int
    health_score: Optional[Decimal] = None
    health_status: Optional[str] = None
    churn_risk_score: Optional[Decimal] = None
    engagement_score: Optional[Decimal] = None
    feature_adoption_score: Optional[Decimal] = None
    business_performance_score: Optional[Decimal] = None
    active_features: list[str] = Field(default_factory=list)


class ShopperBehaviourFacts(BaseModel):
    """
    Deterministic, AI-safe facts representing shopper behaviour.
    Strictly excludes PII (names, emails, billing info, exact address, session IDs).
    """
    model_config = ConfigDict(extra="forbid")

    total_orders: int
    total_spend: Decimal
    average_order_value: Decimal
    customer_lifetime_value: Optional[Decimal] = None
    purchase_frequency: Optional[Decimal] = None
    wishlist_item_count: int
    save_for_later_item_count: int
    campaign_engagement_count: int
    preferred_category: Optional[str] = None
    preferred_size: Optional[str] = None
    lifecycle_stage: Optional[str] = None
    last_purchase_at: Optional[datetime] = None
    segments: list[str] = Field(default_factory=list)
    total_journeys: int = 0
    converted_journeys: int = 0


class ShopperJourneyFacts(BaseModel):
    """Deterministic, AI-safe facts representing a completed shopper interaction episode."""
    model_config = ConfigDict(extra="forbid")

    journey_status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    entry_source: Optional[str] = None
    converted: bool
    touchpoint_count: int
    touchpoint_event_types: list[str] = Field(default_factory=list)
    order_id: Optional[uuid.UUID] = None
    order_total_amount: Optional[Decimal] = None


class CampaignSummaryFacts(BaseModel):
    """Deterministic, AI-safe facts representing campaign configuration and performance."""
    model_config = ConfigDict(extra="forbid")

    campaign_name: str
    campaign_type: str
    campaign_medium: str
    status: str
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    target_segment_name: Optional[str] = None
    delivered_count: int = 0
    opened_count: int = 0
    clicked_count: int = 0
    converted_count: int = 0
    attributed_order_count: int = 0
    attributed_revenue: Decimal = Decimal("0.00")
    open_rate: Decimal = Decimal("0.00")
    click_through_rate: Decimal = Decimal("0.00")
    conversion_rate: Decimal = Decimal("0.00")


class MerchantPerformanceFacts(BaseModel):
    """Deterministic facts representing merchant business performance over a closed month."""
    model_config = ConfigDict(extra="forbid")

    period_start: date
    period_end: date
    total_revenue: Decimal
    order_count: int
    unique_shoppers: int
    new_shoppers: int
    average_order_value: Decimal
    conversion_rate: Decimal
    session_count: int
    converted_session_count: int


class PlatformPerformanceFacts(BaseModel):
    """Deterministic facts representing platform-wide business metrics over a closed month."""
    model_config = ConfigDict(extra="forbid")

    period_start: date
    period_end: date
    active_merchants: int
    new_merchants: int
    installed_merchants: int
    uninstalled_merchants: int
    new_subscriptions: int
    total_revenue: Decimal
    total_orders: int
    active_shoppers: int


class KnowledgeFactPayload(BaseModel):
    """Typed envelope containing knowledge metadata and typed factual content."""
    model_config = ConfigDict(extra="forbid")

    metadata: KnowledgeMetadata
    facts: Union[
        MerchantSummaryFacts,
        ShopperBehaviourFacts,
        ShopperJourneyFacts,
        CampaignSummaryFacts,
        MerchantPerformanceFacts,
        PlatformPerformanceFacts,
    ]


class KnowledgeQdrantPayload(BaseModel):
    """Serialized vector payload contract stored in Qdrant alongside generated embeddings."""
    model_config = ConfigDict(extra="forbid")

    point_id: str
    knowledge_type: str
    entity_type: str
    entity_id: Optional[str] = None
    merchant_id: Optional[str] = None
    shopper_id: Optional[str] = None
    campaign_id: Optional[str] = None
    journey_id: Optional[str] = None
    entity_name: Optional[str] = None
    as_of: str
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    is_current: bool
    summary: str
    access_scope: str
    source_references: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: str
    schema_version: int = 1
    embedding_model: Optional[str] = None
    prompt_version: Optional[str] = None
