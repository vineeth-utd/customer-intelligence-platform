from datetime import date
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.schemas.analytics import (
    CampaignAnalyticsResult,
    MerchantMetricsSummaryResult,
    MerchantMetricsTrendResult,
)
from app.schemas.common import PaginatedResponse
from app.schemas.merchant import MerchantDetailResponse, MerchantSummaryResponse
from app.schemas.shopper import ShopperResponse
from app.schemas.order import OrderResponse

from app.services.analytics import (
    get_campaign_analytics_for_merchant,
    get_merchant_metrics_summary,
    get_merchant_metrics_trend,
)
from app.services.merchant import list_merchants, get_merchant_detail
from app.services.shopper import list_shoppers
from app.services.order import list_orders

router = APIRouter(prefix="/api/v1/merchants", tags=["merchants"])


@router.get("", response_model=PaginatedResponse[MerchantSummaryResponse])
async def read_merchants(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db)
):
    """
    List installed merchants to populate the internal dashboard selector.
    """
    items, total = await list_merchants(session, limit, offset)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{merchant_id}", response_model=MerchantDetailResponse)
async def read_merchant(
    merchant_id: UUID,
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieve basic merchant profile.
    """
    result = await get_merchant_detail(session, merchant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return result


@router.get("/{merchant_id}/shoppers", response_model=PaginatedResponse[ShopperResponse])
async def read_merchant_shoppers(
    merchant_id: UUID,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db)
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
    session: AsyncSession = Depends(get_db)
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
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieve aggregated analytical metrics for a specific merchant.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
        
    result = await get_merchant_metrics_summary(session, merchant_id, start_date, end_date)
    if not result:
        raise HTTPException(status_code=404, detail="Merchant metrics summary not found")
    return result


@router.get("/{merchant_id}/analytics/trend", response_model=List[MerchantMetricsTrendResult])
async def read_merchant_metrics_trend(
    merchant_id: UUID,
    start_date: date,
    end_date: date,
    session: AsyncSession = Depends(get_db)
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
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieve a summary of all campaigns and their performance for a merchant.
    """
    return await get_campaign_analytics_for_merchant(session, merchant_id)
