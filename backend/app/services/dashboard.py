from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import (
    MerchantMetricsSummaryResult,
    PlatformSummaryResult,
)
from app.schemas.dashboard import (
    MerchantDashboardResponse,
    PlatformDashboardResponse,
)
from app.services.analytics import (
    get_campaign_analytics_for_merchant,
    get_conversion_funnel,
    get_feature_metrics_summary,
    get_merchant_metrics_summary,
    get_platform_metrics_trend,
    get_platform_summary,
    get_revenue_analytics,
    get_shopper_behavior_analytics,
    get_shopper_journey_analytics,
)
from app.services.merchant import get_merchant_detail
from app.services.merchant_health import get_merchant_health_with_factors


async def get_platform_dashboard(
    session: AsyncSession, start_date: date, end_date: date
) -> PlatformDashboardResponse:
    """
    Pure composition service providing an atomic view of platform health,
    metric trends, and feature adoption for internal dashboards.
    """
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    summary = await get_platform_summary(session)
    if not summary:
        summary = PlatformSummaryResult(
            total_merchants=0,
            active_merchants=0,
            total_revenue=0,
            total_orders=0,
            active_shoppers=0,
            active_subscriptions=0,
        )

    trends = await get_platform_metrics_trend(session, start_date, end_date)
    features = await get_feature_metrics_summary(session)

    return PlatformDashboardResponse(
        summary=summary,
        trends=trends,
        features=features,
    )


async def get_merchant_dashboard(
    session: AsyncSession, merchant_id: UUID, start_date: date, end_date: date
) -> Optional[MerchantDashboardResponse]:
    """
    Pure composition service coordinating deterministic intelligence capabilities
    for a single merchant overview without duplicating calculations.
    """
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    merchant = await get_merchant_detail(session, merchant_id)
    if not merchant:
        return None

    # Sequential execution on the shared AsyncSession
    health = await get_merchant_health_with_factors(session, merchant_id)
    summary = await get_merchant_metrics_summary(session, merchant_id, start_date, end_date)
    if not summary:
        summary = MerchantMetricsSummaryResult(
            merchant_id=merchant_id,
            revenue=0,
            order_count=0,
            unique_shoppers=0,
            new_shoppers=0,
            session_count=0,
            converted_session_count=0,
            product_view_count=0,
            wishlist_add_count=0,
            save_for_later_count=0,
            add_to_cart_count=0,
            checkout_count=0,
            purchase_count=0,
            conversion_rate=0,
            average_order_value=0,
            platform_login_count=0,
            campaign_created_count=0,
            feature_enable_count=0,
            feature_disable_count=0,
        )

    revenue = await get_revenue_analytics(session, merchant_id, start_date, end_date)
    funnel = await get_conversion_funnel(session, merchant_id, start_date, end_date)
    journeys = await get_shopper_journey_analytics(session, merchant_id, start_date, end_date)
    behavior = await get_shopper_behavior_analytics(session, merchant_id, start_date, end_date)
    campaigns = await get_campaign_analytics_for_merchant(session, merchant_id)

    # In rare cases where sub-services return None for an existing merchant (e.g. edge cases),
    # ensure fallback or pass through safely
    if revenue is None or funnel is None or journeys is None or behavior is None:
        return None

    return MerchantDashboardResponse(
        merchant_id=merchant_id,
        start_date=start_date,
        end_date=end_date,
        merchant=merchant,
        health=health,
        summary=summary,
        revenue=revenue,
        funnel=funnel,
        journeys=journeys,
        behavior=behavior,
        campaigns=campaigns or [],
    )

