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
from app.services.analytics import (
    get_campaign_analytics_for_merchant,
    get_merchant_metrics_summary,
    get_merchant_metrics_trend,
)

router = APIRouter(prefix="/api/v1/merchants", tags=["merchants"])


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
