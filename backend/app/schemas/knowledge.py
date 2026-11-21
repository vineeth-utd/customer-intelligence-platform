from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional, Self, Union
import uuid

from pydantic import BaseModel, ConfigDict, Field, model_validator


# Canonical RFC 4122 namespace for all CIP AI Knowledge Point IDs
CIP_KNOWLEDGE_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "knowledge.cip")


def generate_knowledge_point_id(
    knowledge_type: str | "KnowledgeType",
    entity_id: Optional[uuid.UUID] = None,
    period_start: Optional[date | str] = None,
    period_end: Optional[date | str] = None,
) -> uuid.UUID:
    """
    Generate a deterministic RFC 4122 UUIDv5 point ID for a knowledge item
    matching the canonical CIP AI Knowledge identity rules.
    """
    k_type = knowledge_type.value if isinstance(knowledge_type, KnowledgeType) else knowledge_type

    if k_type == KnowledgeType.MERCHANT_SUMMARY.value:
        if entity_id is None:
            raise ValueError("merchant_summary requires merchant_id")
        name = f"merchant_summary:{entity_id}"
    elif k_type == KnowledgeType.SHOPPER_BEHAVIOUR.value:
        if entity_id is None:
            raise ValueError("shopper_behaviour requires shopper_id")
        name = f"shopper_behaviour:{entity_id}"
    elif k_type == KnowledgeType.SHOPPER_JOURNEY.value:
        if entity_id is None:
            raise ValueError("shopper_journey requires stable journey_id")
        name = f"shopper_journey:{entity_id}"
    elif k_type == KnowledgeType.CAMPAIGN_SUMMARY.value:
        if entity_id is None:
            raise ValueError("campaign_summary requires campaign_id")
        name = f"campaign_summary:{entity_id}"
    elif k_type == KnowledgeType.MERCHANT_PERFORMANCE.value:
        if entity_id is None or period_start is None or period_end is None:
            raise ValueError("merchant_performance requires merchant_id, period_start, and period_end")
        start_str = period_start.isoformat() if isinstance(period_start, date) else str(period_start)
        end_str = period_end.isoformat() if isinstance(period_end, date) else str(period_end)
        name = f"merchant_performance:{entity_id}:{start_str}:{end_str}"
    elif k_type == KnowledgeType.PLATFORM_PERFORMANCE.value:
        if period_start is None or period_end is None:
            raise ValueError("platform_performance requires period_start and period_end")
        start_str = period_start.isoformat() if isinstance(period_start, date) else str(period_start)
        end_str = period_end.isoformat() if isinstance(period_end, date) else str(period_end)
        name = f"platform_performance:{start_str}:{end_str}"
    else:
        raise ValueError(f"Unknown knowledge_type: {knowledge_type}")

    return uuid.uuid5(CIP_KNOWLEDGE_NAMESPACE, name)


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
    Only contains currently authoritative, supported shopper facts (no deferred fields).
    """
    model_config = ConfigDict(extra="forbid")

    total_orders: int
    total_spend: Decimal
    average_order_value: Decimal
    wishlist_item_count: int
    save_for_later_item_count: int
    campaign_engagement_count: int
    preferred_category: Optional[str] = None
    preferred_size: Optional[str] = None
    last_purchase_at: Optional[datetime] = None
    segments: list[str] = Field(default_factory=list)
    total_journeys: int = 0
    converted_journeys: int = 0


class ShopperJourneyFacts(BaseModel):
    """
    Deterministic, AI-safe facts representing a completed shopper interaction episode.
    Preserves retrieval-oriented interaction context (products viewed, searches, cart actions)
    without raw mechanical payload leakage.
    """
    model_config = ConfigDict(extra="forbid")

    journey_status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    entry_source: Optional[str] = None
    converted: bool
    touchpoint_count: int
    touchpoint_event_types: list[str] = Field(default_factory=list)
    products_viewed: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    cart_add_count: int = 0
    checkout_started: bool = False
    order_id: Optional[uuid.UUID] = None
    order_total_amount: Optional[Decimal] = None


class CampaignSummaryFacts(BaseModel):
    """
    Deterministic, AI-safe facts representing campaign configuration, performance,
    attribution, audience response, and journey correlation.
    """
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
    first_touch_conversions: int = 0
    last_touch_conversions: int = 0
    assisted_conversions: int = 0
    first_touch_revenue: Decimal = Decimal("0.00")
    last_touch_revenue: Decimal = Decimal("0.00")
    total_journeys_touched: int = 0
    journey_conversion_rate: Decimal = Decimal("0.00")
    top_drop_off_stages: dict[str, int] = Field(default_factory=dict)
    audience_reached_count: int = 0
    audience_engaged_count: int = 0
    audience_converted_count: int = 0


class MerchantPerformanceFacts(BaseModel):
    """
    Deterministic facts representing merchant business performance over a closed month,
    composed from period-level Business Services.
    """
    model_config = ConfigDict(extra="forbid")

    period_start: date
    period_end: date
    total_revenue: Decimal
    order_count: int
    average_order_value: Decimal
    unique_shoppers: int
    new_shoppers: int
    returning_shoppers: int
    conversion_rate: Decimal
    cart_abandonment_rate: Decimal
    total_journeys: int
    converted_journeys: int
    journey_conversion_rate: Decimal


class PlatformPerformanceFacts(BaseModel):
    """
    Deterministic facts representing platform-wide business metrics over a closed month,
    composed from period-level platform Business Services.
    """
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


class KnowledgeWorkItem(BaseModel):
    """
    Self-contained unit of work representing a single knowledge item to be generated.
    Can be dispatched independently by the knowledge generator or future orchestrators (e.g. Airflow).
    """
    model_config = ConfigDict(extra="forbid")

    knowledge_type: KnowledgeType
    entity_id: Optional[uuid.UUID] = None
    merchant_id: Optional[uuid.UUID] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    as_of: Optional[datetime] = None
    is_current: Optional[bool] = None
    source_watermark: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_requirements(self) -> Self:
        k_type = self.knowledge_type
        if k_type in (
            KnowledgeType.MERCHANT_SUMMARY,
            KnowledgeType.SHOPPER_BEHAVIOUR,
            KnowledgeType.SHOPPER_JOURNEY,
            KnowledgeType.CAMPAIGN_SUMMARY,
        ):
            if self.entity_id is None:
                raise ValueError(f"{k_type.value} requires entity_id")
        elif k_type == KnowledgeType.MERCHANT_PERFORMANCE:
            if self.entity_id is None:
                raise ValueError("merchant_performance requires entity_id (merchant_id)")
            if self.period_start is None or self.period_end is None:
                raise ValueError("merchant_performance requires period_start and period_end")
            if self.period_start > self.period_end:
                raise ValueError("period_start cannot be after period_end")
        elif k_type == KnowledgeType.PLATFORM_PERFORMANCE:
            if self.period_start is None or self.period_end is None:
                raise ValueError("platform_performance requires period_start and period_end")
            if self.period_start > self.period_end:
                raise ValueError("period_start cannot be after period_end")
        return self

    @property
    def point_id(self) -> uuid.UUID:
        return generate_knowledge_point_id(
            knowledge_type=self.knowledge_type,
            entity_id=self.entity_id,
            period_start=self.period_start,
            period_end=self.period_end,
        )


class KnowledgeGenerationResult(BaseModel):
    """Execution result returned from generating a single knowledge work item."""
    model_config = ConfigDict(extra="forbid")

    point_id: uuid.UUID
    knowledge_type: KnowledgeType
    status: KnowledgeStatus
    source_watermark: Optional[datetime] = None
    summary: Optional[str] = None
    error_message: Optional[str] = None
    generated_at: Optional[datetime] = None
    retry_count: int = 0

