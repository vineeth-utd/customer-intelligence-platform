from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.schemas.analytics import (
    FeatureMetricsResult,
    PlatformSummaryResult,
    PlatformTrendResult,
)
from app.services.analytics import (
    get_feature_metrics_summary,
    get_platform_metrics_trend,
    get_platform_summary,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/platform/summary", response_model=PlatformSummaryResult)
async def read_platform_summary(
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieve the platform metrics summary (total merchants, revenue, etc.).
    """
    result = await get_platform_summary(session)
    if not result:
        return PlatformSummaryResult(
            total_merchants=0,
            active_merchants=0,
            total_revenue=0,
            total_orders=0,
            active_shoppers=0,
            active_subscriptions=0
        )
    return result


@router.get("/platform/trend", response_model=List[PlatformTrendResult])
async def read_platform_trend(
    start_date: date,
    end_date: date,
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieve platform metrics over a time period.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")
        
    return await get_platform_metrics_trend(session, start_date, end_date)


@router.get("/features", response_model=List[FeatureMetricsResult])
async def read_feature_metrics(
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieve feature adoption and usage metrics.
    """
    return await get_feature_metrics_summary(session)
