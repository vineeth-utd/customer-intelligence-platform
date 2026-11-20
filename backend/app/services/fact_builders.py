from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.knowledge import (
    CampaignSummaryFacts,
    KnowledgeAccessScope,
    KnowledgeFactPayload,
    KnowledgeMetadata,
    KnowledgeType,
    MerchantPerformanceFacts,
    MerchantSummaryFacts,
    PlatformPerformanceFacts,
    ShopperBehaviourFacts,
    ShopperJourneyFacts,
    SourceReference,
)
from app.services.analytics import (
    get_campaign_analytics_for_campaign,
    get_campaign_attribution,
    get_campaign_audience_analysis,
    get_campaign_journey_correlation,
    get_conversion_funnel,
    get_merchant_metrics_summary,
    get_platform_period_summary,
    get_revenue_analytics,
    get_shopper_behavior_analytics,
    get_shopper_journey_analytics,
)
from app.services.campaign import get_campaign_by_id, get_campaign_detail, list_campaigns
from app.services.journey import (
    get_shopper_journey,
    get_shopper_journey_interaction_context,
    get_shopper_journeys_for_shopper,
)
from app.services.knowledge import generate_knowledge_point_id
from app.services.merchant import get_merchant_detail, get_merchant_features
from app.services.merchant_health import get_merchant_health
from app.services.order import get_order
from app.services.profile import get_merchant_profile, get_shopper_profile
from app.services.segment import get_segments_for_shopper
from app.services.shopper import get_shopper_by_id, list_shoppers


async def build_merchant_summary_facts(
    session: AsyncSession, merchant_id: uuid.UUID, as_of: Optional[datetime] = None
) -> KnowledgeFactPayload:
    """
    Build deterministic facts representing current merchant profile, health, and activity.
    Strictly composed from existing Business Services.
    """
    eval_time = as_of or datetime.now(timezone.utc)
    if eval_time.tzinfo is None:
        eval_time = eval_time.replace(tzinfo=timezone.utc)

    merchant = await get_merchant_detail(session, merchant_id)
    if not merchant:
        raise ValueError(f"Merchant {merchant_id} not found")

    health = await get_merchant_health(session, merchant_id)
    features = await get_merchant_features(session, merchant_id)
    profile = await get_merchant_profile(session, merchant_id)

    if profile is not None:
        total_shoppers = profile.total_shoppers
        total_products = profile.total_products
        total_orders = profile.total_orders
        total_revenue = Decimal(str(profile.total_revenue))
        average_order_value = Decimal(str(profile.average_order_value))
        conversion_rate = Decimal(str(profile.conversion_rate))
        active_campaign_count = profile.active_campaign_count
        enabled_feature_count = profile.enabled_feature_count
    else:
        total_products = 0
        total_orders = 0
        total_revenue = Decimal("0.00")
        average_order_value = Decimal("0.00")
        conversion_rate = Decimal("0.00")
        active_features = [f.feature_key for f in features if f.is_enabled] if features else []
        enabled_feature_count = len(active_features)
        _, total_shoppers = await list_shoppers(session, merchant_id, limit=1, offset=0)
        _, active_campaign_count = await list_campaigns(session, merchant_id, status="active")

    active_feature_keys = [f.feature_key for f in features if f.is_enabled] if features else []

    facts = MerchantSummaryFacts(
        merchant_name=merchant.merchant_name,
        store_currency=merchant.store_currency,
        country=merchant.country,
        timezone=merchant.timezone,
        app_install_status=merchant.app_install_status,
        subscription_plan=merchant.active_subscription.plan_name if merchant.active_subscription else None,
        total_shoppers=total_shoppers,
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        average_order_value=average_order_value,
        conversion_rate=conversion_rate,
        active_campaign_count=active_campaign_count,
        enabled_feature_count=enabled_feature_count,
        health_score=Decimal(str(health.health_score)) if health and health.health_score is not None else None,
        health_status=health.health_status if health else None,
        churn_risk_score=Decimal(str(health.churn_risk_score)) if health and health.churn_risk_score is not None else None,
        engagement_score=Decimal(str(health.engagement_score)) if health and health.engagement_score is not None else None,
        feature_adoption_score=Decimal(str(health.feature_adoption_score)) if health and health.feature_adoption_score is not None else None,
        business_performance_score=Decimal(str(health.business_performance_score)) if health and health.business_performance_score is not None else None,
        active_features=active_feature_keys,
    )

    point_id = generate_knowledge_point_id(KnowledgeType.MERCHANT_SUMMARY, merchant_id)

    metadata = KnowledgeMetadata(
        point_id=point_id,
        knowledge_type=KnowledgeType.MERCHANT_SUMMARY,
        entity_type="merchant",
        entity_id=merchant_id,
        merchant_id=merchant_id,
        entity_name=merchant.merchant_name,
        as_of=eval_time,
        is_current=True,
        access_scope=KnowledgeAccessScope.MERCHANT,
        source_references=[
            SourceReference(source_type="merchants", source_reference=str(merchant_id), as_of=eval_time),
            SourceReference(source_type="merchant_profiles", source_reference=str(merchant_id), as_of=profile.generated_at if profile else eval_time),
            SourceReference(source_type="merchant_health", source_reference=str(merchant_id), as_of=health.calculated_at if health else eval_time),
        ],
    )

    return KnowledgeFactPayload(metadata=metadata, facts=facts)


async def build_shopper_behaviour_facts(
    session: AsyncSession, shopper_id: uuid.UUID, as_of: Optional[datetime] = None
) -> KnowledgeFactPayload:
    """
    Build deterministic facts representing shopper behaviour.
    Strictly excludes PII and deferred profile metrics.
    Composed from existing Business Services.
    """
    eval_time = as_of or datetime.now(timezone.utc)
    if eval_time.tzinfo is None:
        eval_time = eval_time.replace(tzinfo=timezone.utc)

    shopper = await get_shopper_by_id(session, shopper_id)
    if not shopper:
        raise ValueError(f"Shopper {shopper_id} not found")

    profile = await get_shopper_profile(session, shopper_id)
    segments = await get_segments_for_shopper(session, shopper_id)
    journeys = await get_shopper_journeys_for_shopper(session, shopper_id, include_events=False)

    total_orders = profile.total_orders if profile else 0
    total_spend = Decimal(str(profile.total_spend)) if profile else Decimal("0.00")
    average_order_value = Decimal(str(profile.average_order_value)) if profile else Decimal("0.00")
    wishlist_item_count = profile.wishlist_item_count if profile else 0
    save_for_later_item_count = profile.save_for_later_item_count if profile else 0
    campaign_engagement_count = profile.campaign_engagement_count if profile else 0
    preferred_category = profile.preferred_category if profile else None
    preferred_size = profile.preferred_size if profile else None
    last_purchase_at = profile.last_purchase_at if profile else None

    segment_names = [m.segment.segment_name for m in segments if m.segment is not None]
    total_journeys = len(journeys)
    converted_journeys = sum(1 for j in journeys if j.converted)

    facts = ShopperBehaviourFacts(
        total_orders=total_orders,
        total_spend=total_spend,
        average_order_value=average_order_value,
        wishlist_item_count=wishlist_item_count,
        save_for_later_item_count=save_for_later_item_count,
        campaign_engagement_count=campaign_engagement_count,
        preferred_category=preferred_category,
        preferred_size=preferred_size,
        last_purchase_at=last_purchase_at,
        segments=segment_names,
        total_journeys=total_journeys,
        converted_journeys=converted_journeys,
    )

    point_id = generate_knowledge_point_id(KnowledgeType.SHOPPER_BEHAVIOUR, shopper_id)

    metadata = KnowledgeMetadata(
        point_id=point_id,
        knowledge_type=KnowledgeType.SHOPPER_BEHAVIOUR,
        entity_type="shopper",
        entity_id=shopper_id,
        shopper_id=shopper_id,
        merchant_id=shopper.merchant_id,
        as_of=eval_time,
        is_current=True,
        access_scope=KnowledgeAccessScope.MERCHANT,
        source_references=[
            SourceReference(source_type="shoppers", source_reference=str(shopper_id), as_of=eval_time),
            SourceReference(source_type="shopper_profiles", source_reference=str(shopper_id), as_of=profile.generated_at if profile else eval_time),
            SourceReference(source_type="shopper_segment_memberships", source_reference=str(shopper_id), as_of=eval_time),
            SourceReference(source_type="shopper_journeys", source_reference=str(shopper_id), as_of=eval_time),
        ],
    )

    return KnowledgeFactPayload(metadata=metadata, facts=facts)


async def build_shopper_journey_facts(
    session: AsyncSession, journey_id: uuid.UUID, as_of: Optional[datetime] = None
) -> KnowledgeFactPayload:
    """
    Build deterministic facts representing a completed shopper interaction episode.
    Preserves retrieval-oriented interaction context without raw payload leakage.
    OPEN journeys remain excluded and raise ValueError.
    """
    journey = await get_shopper_journey(session, journey_id, include_events=True)
    if not journey:
        raise ValueError(f"Shopper journey {journey_id} not found")

    if journey.journey_status == "OPEN":
        raise ValueError("OPEN journeys remain excluded because they are incomplete and mutable")

    interaction = await get_shopper_journey_interaction_context(session, journey_id)

    order_total_amount: Optional[Decimal] = None
    if journey.converted and journey.order_id:
        order = await get_order(session, journey.order_id)
        if order:
            order_total_amount = Decimal(str(order.total_amount))

    duration_seconds: Optional[int] = None
    if journey.ended_at and journey.started_at:
        duration_seconds = int((journey.ended_at - journey.started_at).total_seconds())

    events = journey.events or []
    touchpoint_count = len(events)
    touchpoint_event_types = [e.event_type for e in events]

    facts = ShopperJourneyFacts(
        journey_status=journey.journey_status,
        started_at=journey.started_at,
        ended_at=journey.ended_at,
        duration_seconds=duration_seconds,
        entry_source=journey.entry_source,
        converted=journey.converted,
        touchpoint_count=touchpoint_count,
        touchpoint_event_types=touchpoint_event_types,
        products_viewed=interaction.get("products_viewed", []),
        search_queries=interaction.get("search_queries", []),
        cart_add_count=interaction.get("cart_add_count", 0),
        checkout_started=interaction.get("checkout_started", False),
        order_id=journey.order_id,
        order_total_amount=order_total_amount,
    )

    point_id = generate_knowledge_point_id(KnowledgeType.SHOPPER_JOURNEY, journey_id)
    eval_as_of = as_of or (journey.ended_at or journey.started_at)
    if eval_as_of.tzinfo is None:
        eval_as_of = eval_as_of.replace(tzinfo=timezone.utc)

    source_refs = [
        SourceReference(source_type="shopper_journeys", source_reference=str(journey_id), as_of=journey.generated_at),
    ]
    if journey.order_id:
        source_refs.append(SourceReference(source_type="orders", source_reference=str(journey.order_id), as_of=journey.ended_at))

    metadata = KnowledgeMetadata(
        point_id=point_id,
        knowledge_type=KnowledgeType.SHOPPER_JOURNEY,
        entity_type="journey",
        entity_id=journey_id,
        journey_id=journey_id,
        shopper_id=journey.shopper_id,
        merchant_id=journey.merchant_id,
        as_of=eval_as_of,
        is_current=False,
        access_scope=KnowledgeAccessScope.MERCHANT,
        source_references=source_refs,
    )

    return KnowledgeFactPayload(metadata=metadata, facts=facts)


async def build_campaign_summary_facts(
    session: AsyncSession, campaign_id: uuid.UUID, as_of: Optional[datetime] = None
) -> KnowledgeFactPayload:
    """
    Build deterministic facts representing campaign configuration, performance,
    multi-perspective attribution, audience response, and journey correlation.
    Strictly composed from existing Business Services.
    """
    eval_time = as_of or datetime.now(timezone.utc)
    if eval_time.tzinfo is None:
        eval_time = eval_time.replace(tzinfo=timezone.utc)

    campaign = await get_campaign_by_id(session, campaign_id)
    if not campaign:
        raise ValueError(f"Campaign {campaign_id} not found")

    detail = await get_campaign_detail(session, campaign.merchant_id, campaign_id)
    target_segment_name = detail.target_segment_name if detail else None

    analytics = await get_campaign_analytics_for_campaign(session, campaign_id)

    c_start = (campaign.start_at or campaign.created_at).date()
    c_end = (campaign.end_at or eval_time).date()
    if c_start > c_end:
        c_start = c_end

    attribution = await get_campaign_attribution(session, campaign_id, c_start, c_end)
    correlation = await get_campaign_journey_correlation(session, campaign_id, c_start, c_end)
    audience = await get_campaign_audience_analysis(session, campaign_id)

    delivered_count = analytics.delivered_count if analytics else 0
    opened_count = analytics.opened_count if analytics else 0
    clicked_count = analytics.clicked_count if analytics else 0
    converted_count = analytics.converted_count if analytics else 0
    attributed_order_count = analytics.attributed_order_count if analytics else 0
    attributed_revenue = Decimal(str(analytics.attributed_revenue)) if analytics else Decimal("0.00")
    open_rate = Decimal(str(analytics.open_rate)) if analytics else Decimal("0.00")
    click_through_rate = Decimal(str(analytics.click_through_rate)) if analytics else Decimal("0.00")
    conversion_rate = Decimal(str(analytics.conversion_rate)) if analytics else Decimal("0.00")

    first_touch_conversions = attribution.first_touch_journey.conversions_count if attribution else 0
    last_touch_conversions = attribution.last_touch_journey.conversions_count if attribution else 0
    assisted_conversions = attribution.assisted_journey.conversions_count if attribution else 0
    first_touch_revenue = Decimal(str(attribution.first_touch_journey.attributed_revenue)) if attribution else Decimal("0.00")
    last_touch_revenue = Decimal(str(attribution.last_touch_journey.attributed_revenue)) if attribution else Decimal("0.00")

    total_journeys_touched = correlation.total_journeys_touched if correlation else 0
    journey_conversion_rate = Decimal(str(correlation.journey_conversion_rate)) if correlation else Decimal("0.00")
    top_drop_off_stages = correlation.drop_off_stages if correlation else {}

    audience_reached_count = audience.unique_shoppers_reached if audience else 0
    audience_engaged_count = audience.unique_shoppers_engaged if audience else 0
    audience_converted_count = audience.unique_shoppers_converted if audience else 0

    facts = CampaignSummaryFacts(
        campaign_name=campaign.campaign_name,
        campaign_type=campaign.campaign_type,
        campaign_medium=campaign.campaign_medium,
        status=campaign.status,
        start_at=campaign.start_at,
        end_at=campaign.end_at,
        target_segment_name=target_segment_name,
        delivered_count=delivered_count,
        opened_count=opened_count,
        clicked_count=clicked_count,
        converted_count=converted_count,
        attributed_order_count=attributed_order_count,
        attributed_revenue=attributed_revenue,
        open_rate=open_rate,
        click_through_rate=click_through_rate,
        conversion_rate=conversion_rate,
        first_touch_conversions=first_touch_conversions,
        last_touch_conversions=last_touch_conversions,
        assisted_conversions=assisted_conversions,
        first_touch_revenue=first_touch_revenue,
        last_touch_revenue=last_touch_revenue,
        total_journeys_touched=total_journeys_touched,
        journey_conversion_rate=journey_conversion_rate,
        top_drop_off_stages=top_drop_off_stages,
        audience_reached_count=audience_reached_count,
        audience_engaged_count=audience_engaged_count,
        audience_converted_count=audience_converted_count,
    )

    point_id = generate_knowledge_point_id(KnowledgeType.CAMPAIGN_SUMMARY, campaign_id)

    metadata = KnowledgeMetadata(
        point_id=point_id,
        knowledge_type=KnowledgeType.CAMPAIGN_SUMMARY,
        entity_type="campaign",
        entity_id=campaign_id,
        campaign_id=campaign_id,
        merchant_id=campaign.merchant_id,
        entity_name=campaign.campaign_name,
        as_of=eval_time,
        is_current=True,
        access_scope=KnowledgeAccessScope.MERCHANT,
        source_references=[
            SourceReference(source_type="campaigns", source_reference=str(campaign_id), as_of=eval_time),
            SourceReference(source_type="campaign_analytics", source_reference=str(campaign_id), as_of=eval_time),
        ],
    )

    return KnowledgeFactPayload(metadata=metadata, facts=facts)


async def build_merchant_performance_facts(
    session: AsyncSession,
    merchant_id: uuid.UUID,
    period_start: date,
    period_end: date,
    as_of: Optional[datetime] = None,
) -> KnowledgeFactPayload:
    """
    Build deterministic facts representing merchant business performance over a closed month.
    Strictly composed from existing period-level Business Services without local aggregations.
    """
    if period_start > period_end:
        raise ValueError("period_start cannot be after period_end")

    eval_time = as_of or datetime.now(timezone.utc)
    if eval_time.tzinfo is None:
        eval_time = eval_time.replace(tzinfo=timezone.utc)

    metrics = await get_merchant_metrics_summary(session, merchant_id, period_start, period_end)
    revenue = await get_revenue_analytics(session, merchant_id, period_start, period_end)
    funnel = await get_conversion_funnel(session, merchant_id, period_start, period_end)
    shopper_behavior = await get_shopper_behavior_analytics(session, merchant_id, period_start, period_end)
    journey_analytics = await get_shopper_journey_analytics(session, merchant_id, period_start, period_end)

    total_revenue = Decimal(str(revenue.total_revenue)) if revenue else (Decimal(str(metrics.revenue)) if metrics else Decimal("0.00"))
    order_count = revenue.total_orders if revenue else (metrics.order_count if metrics else 0)
    average_order_value = Decimal(str(revenue.average_order_value)) if revenue else (Decimal(str(metrics.average_order_value)) if metrics else Decimal("0.00"))
    unique_shoppers = metrics.unique_shoppers if metrics else (shopper_behavior.total_active_shoppers if shopper_behavior else 0)
    new_shoppers = metrics.new_shoppers if metrics else (shopper_behavior.new_shoppers if shopper_behavior else 0)
    returning_shoppers = shopper_behavior.returning_shoppers if shopper_behavior else 0
    conversion_rate = Decimal(str(metrics.conversion_rate)) if metrics else (Decimal(str(funnel.overall_conversion_rate)) if funnel else Decimal("0.00"))
    cart_abandonment_rate = Decimal(str(funnel.cart_abandonment_rate)) if funnel else Decimal("0.00")
    total_journeys = journey_analytics.total_journeys if journey_analytics else 0
    converted_journeys = journey_analytics.converted_journeys if journey_analytics else 0
    journey_conversion_rate = Decimal(str(journey_analytics.journey_conversion_rate)) if journey_analytics else Decimal("0.00")

    facts = MerchantPerformanceFacts(
        period_start=period_start,
        period_end=period_end,
        total_revenue=total_revenue,
        order_count=order_count,
        average_order_value=average_order_value,
        unique_shoppers=unique_shoppers,
        new_shoppers=new_shoppers,
        returning_shoppers=returning_shoppers,
        conversion_rate=conversion_rate,
        cart_abandonment_rate=cart_abandonment_rate,
        total_journeys=total_journeys,
        converted_journeys=converted_journeys,
        journey_conversion_rate=journey_conversion_rate,
    )

    point_id = generate_knowledge_point_id(
        KnowledgeType.MERCHANT_PERFORMANCE, merchant_id, period_start, period_end
    )

    metadata = KnowledgeMetadata(
        point_id=point_id,
        knowledge_type=KnowledgeType.MERCHANT_PERFORMANCE,
        entity_type="merchant",
        entity_id=merchant_id,
        merchant_id=merchant_id,
        period_start=period_start,
        period_end=period_end,
        as_of=eval_time,
        is_current=False,
        access_scope=KnowledgeAccessScope.MERCHANT,
        source_references=[
            SourceReference(
                source_type="merchant_metrics_daily",
                source_reference={
                    "merchant_id": str(merchant_id),
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                },
                as_of=eval_time,
            ),
        ],
    )

    return KnowledgeFactPayload(metadata=metadata, facts=facts)


async def build_platform_performance_facts(
    session: AsyncSession,
    period_start: date,
    period_end: date,
    as_of: Optional[datetime] = None,
) -> KnowledgeFactPayload:
    """
    Build deterministic facts representing platform-wide business metrics over a closed month.
    Strictly composed from period-level platform Business Services.
    """
    if period_start > period_end:
        raise ValueError("period_start cannot be after period_end")

    eval_time = as_of or datetime.now(timezone.utc)
    if eval_time.tzinfo is None:
        eval_time = eval_time.replace(tzinfo=timezone.utc)

    summary = await get_platform_period_summary(session, period_start, period_end)

    facts = PlatformPerformanceFacts(
        period_start=period_start,
        period_end=period_end,
        active_merchants=summary["active_merchants"] if summary else 0,
        new_merchants=summary["new_merchants"] if summary else 0,
        installed_merchants=summary["installed_merchants"] if summary else 0,
        uninstalled_merchants=summary["uninstalled_merchants"] if summary else 0,
        new_subscriptions=summary["new_subscriptions"] if summary else 0,
        total_revenue=summary["total_revenue"] if summary else Decimal("0.00"),
        total_orders=summary["order_count"] if summary else 0,
        active_shoppers=summary["active_shoppers"] if summary else 0,
    )

    point_id = generate_knowledge_point_id(
        KnowledgeType.PLATFORM_PERFORMANCE, period_start=period_start, period_end=period_end
    )

    metadata = KnowledgeMetadata(
        point_id=point_id,
        knowledge_type=KnowledgeType.PLATFORM_PERFORMANCE,
        entity_type="platform",
        entity_id=None,
        merchant_id=None,
        period_start=period_start,
        period_end=period_end,
        as_of=eval_time,
        is_current=False,
        access_scope=KnowledgeAccessScope.INTERNAL,
        source_references=[
            SourceReference(
                source_type="platform_metrics_daily",
                source_reference={
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                },
                as_of=eval_time,
            ),
        ],
    )

    return KnowledgeFactPayload(metadata=metadata, facts=facts)
