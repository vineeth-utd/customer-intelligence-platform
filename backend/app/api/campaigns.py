from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_merchant_access
from app.dependencies.db import get_db
from app.schemas.analytics import (
    CampaignAttributionResult,
    CampaignAudienceAnalysisResult,
    CampaignJourneyCorrelationResult,
    CampaignPerformanceDetailResult,
)
from app.schemas.auth import Principal
from app.schemas.campaign import (
    CampaignDetailResponse,
    CampaignStatus,
    CampaignSummaryResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.analytics import (
    get_campaign_attribution,
    get_campaign_audience_analysis,
    get_campaign_journey_correlation,
    get_campaign_performance,
)
from app.services.campaign import (
    get_campaign_detail,
    list_campaigns,
    verify_campaign_ownership,
)

router = APIRouter(prefix="/api/v1/merchants/{merchant_id}/campaigns", tags=["campaigns"])


@router.get("", response_model=PaginatedResponse[CampaignSummaryResponse])
async def read_merchant_campaigns(
    merchant_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[CampaignStatus] = Query(default=None),
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    List campaigns for a merchant with pagination and optional status filtering.
    """
    items, total = await list_campaigns(
        session,
        merchant_id,
        limit=limit,
        offset=offset,
        status=status.value if status else None,
    )
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
async def read_campaign(
    merchant_id: UUID,
    campaign_id: UUID,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve single campaign details, including target segment name, ensuring tenant ownership isolation.
    """
    campaign = await get_campaign_detail(session, merchant_id, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.get("/{campaign_id}/performance", response_model=CampaignPerformanceDetailResult)
async def read_campaign_performance(
    merchant_id: UUID,
    campaign_id: UUID,
    start_date: date = Query(...),
    end_date: date = Query(...),
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve unified campaign delivery, engagement trends, and period comparison.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")

    camp = await verify_campaign_ownership(session, merchant_id, campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")

    result = await get_campaign_performance(session, campaign_id, start_date, end_date)
    if not result:
        raise HTTPException(status_code=404, detail="Campaign performance not found")
    return result


@router.get("/{campaign_id}/attribution", response_model=CampaignAttributionResult)
async def read_campaign_attribution(
    merchant_id: UUID,
    campaign_id: UUID,
    start_date: date = Query(...),
    end_date: date = Query(...),
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve deterministic multi-perspective attribution for a campaign.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")

    camp = await verify_campaign_ownership(session, merchant_id, campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")

    result = await get_campaign_attribution(session, campaign_id, start_date, end_date)
    if not result:
        raise HTTPException(status_code=404, detail="Campaign attribution not found")
    return result


@router.get("/{campaign_id}/journey-correlation", response_model=CampaignJourneyCorrelationResult)
async def read_campaign_journey_correlation(
    merchant_id: UUID,
    campaign_id: UUID,
    start_date: date = Query(...),
    end_date: date = Query(...),
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve shopper journey outcome distribution, duration, and drop-off stages for a campaign.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")

    camp = await verify_campaign_ownership(session, merchant_id, campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")

    result = await get_campaign_journey_correlation(session, campaign_id, start_date, end_date)
    if not result:
        raise HTTPException(status_code=404, detail="Campaign journey correlation not found")
    return result


@router.get("/{campaign_id}/audience", response_model=CampaignAudienceAnalysisResult)
async def read_campaign_audience(
    merchant_id: UUID,
    campaign_id: UUID,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve reach, engagement, and conversion analysis across target and current segments.
    """
    camp = await verify_campaign_ownership(session, merchant_id, campaign_id)
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")

    result = await get_campaign_audience_analysis(session, campaign_id)
    if not result:
        raise HTTPException(status_code=404, detail="Campaign audience analysis not found")
    return result

