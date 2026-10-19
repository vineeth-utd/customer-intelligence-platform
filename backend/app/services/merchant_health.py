import logging
import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.merchant import (
    get_active_subscription,
    get_merchant_by_id,
    get_plan_by_key,
)
from app.data_access.merchant_health import (
    get_merchant_health as dal_get_merchant_health,
    list_merchant_health_paginated as dal_list_merchant_health_paginated,
    upsert_merchant_health,
)
from app.data_access.merchant_journey import get_merchant_journeys_by_merchant
from app.data_access.profile import get_merchant_profile
from app.models.merchant import MerchantFeature, PlanFeature, PlatformFeature
from app.models.merchant_health import MerchantHealth
from app.models.metrics import MerchantMetricsDaily
from app.reference_data.plans import PlanKey
from app.services.merchant_health_rules import (
    calculate_business_performance_score,
    calculate_engagement_score,
    calculate_feature_adoption_score,
    calculate_overall_health,
)

logger = logging.getLogger(__name__)


async def _resolve_entitled_and_enabled_features(
    session: AsyncSession, merchant_id: uuid.UUID
) -> tuple[list[str], list[str]]:
    """
    Resolves entitled feature keys based on the merchant's active plan, falling back
    deterministically to the canonical Free plan entitlements, and lists currently enabled features.
    """
    # 1. Resolve Plan
    sub = await get_active_subscription(session, merchant_id)
    plan_id: uuid.UUID | None = sub.plan_id if sub else None

    if plan_id is None:
        free_plan = await get_plan_by_key(session, PlanKey.FREE)
        if free_plan:
            plan_id = free_plan.plan_id

    # 2. Query entitled features
    entitled_feature_keys: list[str] = []
    if plan_id is not None:
        stmt_entitled = (
            select(PlatformFeature.feature_key)
            .join(PlanFeature, PlatformFeature.feature_id == PlanFeature.feature_id)
            .where(PlanFeature.plan_id == plan_id)
        )
        res_entitled = await session.execute(stmt_entitled)
        entitled_feature_keys = list(res_entitled.scalars().all())

    # 3. Query enabled features for the merchant
    stmt_enabled = (
        select(PlatformFeature.feature_key)
        .join(MerchantFeature, PlatformFeature.feature_id == MerchantFeature.feature_id)
        .where(
            MerchantFeature.merchant_id == merchant_id,
            MerchantFeature.is_enabled.is_(True),
        )
    )
    res_enabled = await session.execute(stmt_enabled)
    enabled_feature_keys = list(res_enabled.scalars().all())

    return entitled_feature_keys, enabled_feature_keys


async def _get_recent_and_prior_analytics(
    session: AsyncSession, merchant_id: uuid.UUID, now: datetime
) -> tuple[int, int, int, int, int, int]:
    """
    Queries aggregated order and session counts for the recent 14-day window and prior 14-day window.
    Returns (recent_orders, prior_orders, recent_sessions, recent_converted, prior_sessions, prior_converted).
    """
    recent_start = now.date() - timedelta(days=14)
    recent_end = now.date()
    prior_start = now.date() - timedelta(days=28)

    stmt_recent = (
        select(
            func.coalesce(func.sum(MerchantMetricsDaily.order_count), 0),
            func.coalesce(func.sum(MerchantMetricsDaily.session_count), 0),
            func.coalesce(func.sum(MerchantMetricsDaily.converted_session_count), 0),
        )
        .where(
            MerchantMetricsDaily.merchant_id == merchant_id,
            MerchantMetricsDaily.metric_date >= recent_start,
            MerchantMetricsDaily.metric_date <= recent_end,
        )
    )
    res_recent = await session.execute(stmt_recent)
    recent_row = res_recent.fetchone()
    recent_orders = int(recent_row[0]) if recent_row else 0
    recent_sessions = int(recent_row[1]) if recent_row else 0
    recent_converted = int(recent_row[2]) if recent_row else 0

    stmt_prior = (
        select(
            func.coalesce(func.sum(MerchantMetricsDaily.order_count), 0),
            func.coalesce(func.sum(MerchantMetricsDaily.session_count), 0),
            func.coalesce(func.sum(MerchantMetricsDaily.converted_session_count), 0),
        )
        .where(
            MerchantMetricsDaily.merchant_id == merchant_id,
            MerchantMetricsDaily.metric_date >= prior_start,
            MerchantMetricsDaily.metric_date < recent_start,
        )
    )
    res_prior = await session.execute(stmt_prior)
    prior_row = res_prior.fetchone()
    prior_orders = int(prior_row[0]) if prior_row else 0
    prior_sessions = int(prior_row[1]) if prior_row else 0
    prior_converted = int(prior_row[2]) if prior_row else 0

    return recent_orders, prior_orders, recent_sessions, recent_converted, prior_sessions, prior_converted


async def generate_merchant_health_callback(
    session: AsyncSession, merchant_id: uuid.UUID, evaluation_time: datetime | None = None
) -> None:
    """
    Incremental generator callback for evaluating and persisting MerchantHealth.
    Consumes authoritative signals across operational merchant, subscription,
    profile, journey, and analytics domains.
    """
    merchant = await get_merchant_by_id(session, merchant_id)
    if not merchant:
        return

    now = evaluation_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # 1. Operational & Subscription data
    sub = await get_active_subscription(session, merchant_id)
    subscription_status = sub.status if sub else None

    # 2. Feature Entitlements & Adoption
    entitled_keys, enabled_keys = await _resolve_entitled_and_enabled_features(session, merchant_id)
    feature_score, _ = calculate_feature_adoption_score(entitled_keys, enabled_keys)

    # 3. Journey & Profile data
    journeys = await get_merchant_journeys_by_merchant(session, merchant_id)
    active_journey = journeys[0] if journeys else None
    journey_status = active_journey.journey_status if active_journey else None

    profile = await get_merchant_profile(session, merchant_id)
    active_campaigns = profile.active_campaign_count if profile else 0
    total_campaigns = profile.total_campaigns if profile else 0
    total_orders_all_time = profile.total_orders if profile else 0
    last_order_at = profile.last_order_at if profile else None

    # 4. Engagement Score
    engagement_score, _ = calculate_engagement_score(
        app_install_status=merchant.app_install_status,
        journey_status=journey_status,
        last_active_at=merchant.last_active_at,
        active_campaign_count=active_campaigns,
        total_campaigns=total_campaigns,
        evaluation_time=now,
        created_at=merchant.created_at,
    )

    # 5. Business Performance Score
    r_orders, p_orders, r_sess, r_conv, p_sess, p_conv = await _get_recent_and_prior_analytics(
        session, merchant_id, now
    )
    biz_score, _ = calculate_business_performance_score(
        recent_orders=r_orders,
        prior_orders=p_orders,
        recent_sessions=r_sess,
        recent_converted=r_conv,
        prior_sessions=p_sess,
        prior_converted=p_conv,
        total_orders_all_time=total_orders_all_time,
        last_order_at=last_order_at,
        evaluation_time=now,
        created_at=merchant.created_at,
    )

    # 6. Overall Composite Health Score & Churn Risk
    health_score, health_status, churn_risk_score, _ = calculate_overall_health(
        engagement_score=engagement_score,
        feature_adoption_score=feature_score,
        business_performance_score=biz_score,
        app_install_status=merchant.app_install_status,
        subscription_status=subscription_status,
    )

    # 7. Persist MerchantHealth idempotently
    await upsert_merchant_health(
        session,
        merchant_id=merchant_id,
        health_score=health_score,
        health_status=health_status,
        churn_risk_score=churn_risk_score,
        engagement_score=engagement_score,
        feature_adoption_score=feature_score,
        business_performance_score=biz_score,
        calculated_at=now,
    )


async def get_merchant_health(
    session: AsyncSession, merchant_id: uuid.UUID
) -> MerchantHealth | None:
    """Retrieve the persisted MerchantHealth record for a merchant."""
    return await dal_get_merchant_health(session, merchant_id)


async def get_merchant_health_with_factors(
    session: AsyncSession, merchant_id: uuid.UUID, evaluation_time: datetime | None = None
) -> dict[str, Any] | None:
    """
    Retrieves the MerchantHealth record and compiles the structured contributing factors
    breakdown for explainability in Customer Success dashboards and AI investigations.
    """
    health = await dal_get_merchant_health(session, merchant_id)
    if not health:
        return None

    merchant = await get_merchant_by_id(session, merchant_id)
    if not merchant:
        return None

    now = evaluation_time or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    sub = await get_active_subscription(session, merchant_id)
    subscription_status = sub.status if sub else None

    entitled_keys, enabled_keys = await _resolve_entitled_and_enabled_features(session, merchant_id)
    _, feature_factors = calculate_feature_adoption_score(entitled_keys, enabled_keys)

    journeys = await get_merchant_journeys_by_merchant(session, merchant_id)
    active_journey = journeys[0] if journeys else None
    journey_status = active_journey.journey_status if active_journey else None

    profile = await get_merchant_profile(session, merchant_id)
    active_campaigns = profile.active_campaign_count if profile else 0
    total_campaigns = profile.total_campaigns if profile else 0
    total_orders_all_time = profile.total_orders if profile else 0
    last_order_at = profile.last_order_at if profile else None

    _, engagement_factors = calculate_engagement_score(
        app_install_status=merchant.app_install_status,
        journey_status=journey_status,
        last_active_at=merchant.last_active_at,
        active_campaign_count=active_campaigns,
        total_campaigns=total_campaigns,
        evaluation_time=now,
        created_at=merchant.created_at,
    )

    r_orders, p_orders, r_sess, r_conv, p_sess, p_conv = await _get_recent_and_prior_analytics(
        session, merchant_id, now
    )
    _, biz_factors = calculate_business_performance_score(
        recent_orders=r_orders,
        prior_orders=p_orders,
        recent_sessions=r_sess,
        recent_converted=r_conv,
        prior_sessions=p_sess,
        prior_converted=p_conv,
        total_orders_all_time=total_orders_all_time,
        last_order_at=last_order_at,
        evaluation_time=now,
        created_at=merchant.created_at,
    )

    _, _, _, alerts = calculate_overall_health(
        engagement_score=float(health.engagement_score),
        feature_adoption_score=float(health.feature_adoption_score),
        business_performance_score=float(health.business_performance_score),
        app_install_status=merchant.app_install_status,
        subscription_status=subscription_status,
    )

    return {
        "merchant_id": health.merchant_id,
        "health_score": float(health.health_score),
        "health_status": health.health_status,
        "churn_risk_score": float(health.churn_risk_score),
        "engagement_score": float(health.engagement_score),
        "feature_adoption_score": float(health.feature_adoption_score),
        "business_performance_score": float(health.business_performance_score),
        "calculated_at": health.calculated_at,
        "contributing_factors": {
            "feature_adoption": feature_factors,
            "engagement": engagement_factors,
            "business_performance": biz_factors,
            "subscription": {
                "status": subscription_status,
                "plan_key": sub.plan.plan_key if (sub and sub.plan) else (PlanKey.FREE.value if not sub else None),
                "billing_cycle": sub.billing_cycle if sub else None,
            },
            "risk_alerts": alerts,
        },
    }


async def list_merchant_health(
    session: AsyncSession,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[Sequence[MerchantHealth], int]:
    """Retrieve paginated merchant health assessments."""
    return await dal_list_merchant_health_paginated(
        session, status_filter=status_filter, limit=limit, offset=offset
    )
