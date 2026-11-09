from datetime import date
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_internal_principal, require_merchant_access
from app.dependencies.db import get_db
from app.schemas.analytics import (
    CampaignAnalyticsResult,
    ConversionFunnelResult,
    MerchantMetricsSummaryResult,
    MerchantMetricsTrendResult,
    RevenueAnalyticsResult,
    ShopperBehaviorAnalyticsResult,
    ShopperJourneyAnalyticsResult,
)
from app.schemas.auth import Principal
from app.schemas.common import PaginatedResponse
from app.schemas.merchant import (
    MerchantDetailResponse,
    MerchantFeatureResponse,
    MerchantHealthResponse,
    MerchantJourneyDetailResponse,
    MerchantJourneyResponse,
    MerchantProfileResponse,
    MerchantSummaryResponse,
    SubscriptionResponse,
)
from app.schemas.order import OrderResponse
from app.schemas.shopper import ShopperResponse
from app.services.analytics import (
    get_campaign_analytics_for_merchant,
    get_conversion_funnel,
    get_merchant_metrics_summary,
    get_merchant_metrics_trend,
    get_revenue_analytics,
    get_shopper_behavior_analytics,
    get_shopper_journey_analytics,
)
from app.services.merchant import (
    get_merchant_detail,
    get_merchant_features,
    get_merchant_subscription_detail,
    list_merchants,
)
from app.services.merchant_health import get_merchant_health_with_factors
from app.services.merchant_journey import (
    get_merchant_journey,
    get_merchant_journeys_for_merchant,
)
from app.services.order import list_orders
from app.services.profile import get_merchant_profile
from app.services.shopper import list_shoppers

router = APIRouter(prefix="/api/v1/merchants", tags=["merchants"])


@router.get("", response_model=PaginatedResponse[MerchantSummaryResponse])
async def read_merchants(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_internal_principal),
):
    """
    List installed merchants to populate the internal dashboard selector.
    Requires INTERNAL platform-wide access.
    """
    items, total = await list_merchants(session, limit, offset)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{merchant_id}", response_model=MerchantDetailResponse)
async def read_merchant(
    merchant_id: UUID,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve basic merchant profile.
    """
    result = await get_merchant_detail(session, merchant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return result


@router.get("/{merchant_id}/profile", response_model=MerchantProfileResponse)
async def read_merchant_profile(
    merchant_id: UUID,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve the calculated merchant profile data product.
    """
    profile = await get_merchant_profile(session, merchant_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Merchant profile not found")
    return profile


@router.get("/{merchant_id}/health", response_model=MerchantHealthResponse)
async def read_merchant_health(
    merchant_id: UUID,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve calculated merchant health metrics and explainable contributing factors.
    """
    health = await get_merchant_health_with_factors(session, merchant_id)
    if not health:
        raise HTTPException(status_code=404, detail="Merchant health not found")
    return health


@router.get("/{merchant_id}/journeys", response_model=List[MerchantJourneyResponse])
async def read_merchant_journeys(
    merchant_id: UUID,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve lifecycle journeys for a merchant.
    """
    return await get_merchant_journeys_for_merchant(session, merchant_id, include_events=False)


@router.get("/{merchant_id}/journeys/{merchant_journey_id}", response_model=MerchantJourneyDetailResponse)
async def read_merchant_journey_detail(
    merchant_id: UUID,
    merchant_journey_id: UUID,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve a single merchant journey with its ordered milestones and events.
    """
    journey = await get_merchant_journey(session, merchant_journey_id, include_events=True)
    if not journey or journey.merchant_id != merchant_id:
        raise HTTPException(status_code=404, detail="Merchant journey not found")
    return journey


@router.get("/{merchant_id}/features", response_model=List[MerchantFeatureResponse])
async def read_merchant_features(
    merchant_id: UUID,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve feature entitlements and enablement state for a merchant.
    """
    return await get_merchant_features(session, merchant_id)


@router.get("/{merchant_id}/subscription", response_model=SubscriptionResponse)
async def read_merchant_subscription(
    merchant_id: UUID,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve current/latest subscription lifecycle state for a merchant.
    """
    subscription = await get_merchant_subscription_detail(session, merchant_id)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found for merchant")
    return subscription


@router.get("/{merchant_id}/shoppers", response_model=PaginatedResponse[ShopperResponse])
async def read_merchant_shoppers(
    merchant_id: UUID,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Provide recent shopper activity for dashboard drill-down views.
    """
    items, total = await list_shoppers(session, merchant_id, limit, offset)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{merchant_id}/orders", response_model=PaginatedResponse[OrderResponse])
async def read_merchant_orders(
    merchant_id: UUID,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Provide recent business activity (orders) for dashboard drill-down views.
    """
    items, total = await list_orders(session, merchant_id, limit, offset)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{merchant_id}/analytics/summary", response_model=MerchantMetricsSummaryResult)
async def read_merchant_metrics_summary(
    merchant_id: UUID,
    start_date: date,
    end_date: date,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve aggregated analytical metrics for a specific merchant.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
        
    result = await get_merchant_metrics_summary(session, merchant_id, start_date, end_date)
    if not result:
        return MerchantMetricsSummaryResult(
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
            feature_disable_count=0
        )
    return result


@router.get("/{merchant_id}/analytics/trend", response_model=List[MerchantMetricsTrendResult])
async def read_merchant_metrics_trend(
    merchant_id: UUID,
    start_date: date,
    end_date: date,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve time-series analytical trends for a specific merchant.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
        
    return await get_merchant_metrics_trend(session, merchant_id, start_date, end_date)


@router.get("/{merchant_id}/campaigns/analytics", response_model=List[CampaignAnalyticsResult])
async def read_campaign_analytics(
    merchant_id: UUID,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve a summary of all campaigns and their performance for a merchant.
    """
    return await get_campaign_analytics_for_merchant(session, merchant_id)


@router.get("/{merchant_id}/analytics/funnel", response_model=ConversionFunnelResult)
async def read_merchant_conversion_funnel(
    merchant_id: UUID,
    start_date: date,
    end_date: date,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve store-level conversion funnel and secondary engagement metrics.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")

    result = await get_conversion_funnel(session, merchant_id, start_date, end_date)
    if result is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return result


@router.get("/{merchant_id}/analytics/journeys", response_model=ShopperJourneyAnalyticsResult)
async def read_merchant_shopper_journeys_analytics(
    merchant_id: UUID,
    start_date: date,
    end_date: date,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve aggregate shopper journey multi-touch outcome and funnel analytics.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")

    result = await get_shopper_journey_analytics(session, merchant_id, start_date, end_date)
    if result is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return result


@router.get("/{merchant_id}/analytics/behavior", response_model=ShopperBehaviorAnalyticsResult)
async def read_merchant_shopper_behavior_analytics(
    merchant_id: UUID,
    start_date: date,
    end_date: date,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve store-level shopper behavioral analytics (new vs returning, repeat purchase rate).
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")

    result = await get_shopper_behavior_analytics(session, merchant_id, start_date, end_date)
    if result is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return result


@router.get("/{merchant_id}/analytics/revenue", response_model=RevenueAnalyticsResult)
async def read_merchant_revenue_analytics(
    merchant_id: UUID,
    start_date: date,
    end_date: date,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve store-level revenue, order count, AOV, and period-over-period comparison analytics.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")

    result = await get_revenue_analytics(session, merchant_id, start_date, end_date)
    if result is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return result

