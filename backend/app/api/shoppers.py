from datetime import date
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_merchant_access
from app.dependencies.db import get_db
from app.schemas.auth import Principal
from app.schemas.common import PaginatedResponse
from app.schemas.order import OrderResponse
from app.schemas.shopper import (
    ShopperActivityEventResponse,
    ShopperJourneyDetailResponse,
    ShopperJourneyResponse,
    ShopperProfileResponse,
    ShopperResponse,
    ShopperSegmentMembershipResponse,
)
from app.services.journey import get_shopper_journey, get_shopper_journeys_for_shopper
from app.services.order import list_shopper_orders
from app.services.profile import get_shopper_profile
from app.services.segment import get_segments_for_shopper
from app.services.shopper import get_shopper, list_shopper_activity

router = APIRouter(prefix="/api/v1/merchants/{merchant_id}/shoppers", tags=["shoppers"])


@router.get("/{shopper_id}", response_model=ShopperResponse)
async def read_shopper(
    merchant_id: UUID,
    shopper_id: UUID,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve single shopper profile details, ensuring merchant ownership isolation.
    """
    shopper = await get_shopper(session, merchant_id, shopper_id)
    if not shopper:
        raise HTTPException(status_code=404, detail="Shopper not found")
    return shopper


@router.get("/{shopper_id}/profile", response_model=ShopperProfileResponse)
async def read_shopper_profile(
    merchant_id: UUID,
    shopper_id: UUID,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve calculated analytical profile for a specific shopper.
    """
    shopper = await get_shopper(session, merchant_id, shopper_id)
    if not shopper:
        raise HTTPException(status_code=404, detail="Shopper not found")

    profile = await get_shopper_profile(session, shopper_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Shopper profile not found")
    return profile


@router.get("/{shopper_id}/journeys", response_model=List[ShopperJourneyResponse])
async def read_shopper_journeys(
    merchant_id: UUID,
    shopper_id: UUID,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve 7-day behavioural journeys for a shopper.
    """
    shopper = await get_shopper(session, merchant_id, shopper_id)
    if not shopper:
        raise HTTPException(status_code=404, detail="Shopper not found")

    return await get_shopper_journeys_for_shopper(session, shopper_id, include_events=False)


@router.get("/{shopper_id}/journeys/{journey_id}", response_model=ShopperJourneyDetailResponse)
async def read_shopper_journey_detail(
    merchant_id: UUID,
    shopper_id: UUID,
    journey_id: UUID,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve a single shopper journey with its chronological touchpoint events.
    """
    shopper = await get_shopper(session, merchant_id, shopper_id)
    if not shopper:
        raise HTTPException(status_code=404, detail="Shopper not found")

    journey = await get_shopper_journey(session, journey_id, include_events=True)
    if not journey or journey.merchant_id != merchant_id or journey.shopper_id != shopper_id:
        raise HTTPException(status_code=404, detail="Shopper journey not found")
    return journey


@router.get("/{shopper_id}/orders", response_model=PaginatedResponse[OrderResponse])
async def read_shopper_orders(
    merchant_id: UUID,
    shopper_id: UUID,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve purchase history for a shopper under a merchant.
    """
    shopper = await get_shopper(session, merchant_id, shopper_id)
    if not shopper:
        raise HTTPException(status_code=404, detail="Shopper not found")

    items, total = await list_shopper_orders(session, merchant_id, shopper_id, limit, offset)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{shopper_id}/segments", response_model=List[ShopperSegmentMembershipResponse])
async def read_shopper_segments(
    merchant_id: UUID,
    shopper_id: UUID,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve current segment memberships for a shopper.
    """
    shopper = await get_shopper(session, merchant_id, shopper_id)
    if not shopper:
        raise HTTPException(status_code=404, detail="Shopper not found")

    memberships = await get_segments_for_shopper(session, shopper_id)
    return [
        ShopperSegmentMembershipResponse(
            segment_id=m.segment_id,
            segment_name=m.segment.segment_name,
            generated_at=m.generated_at,
        )
        for m in memberships
    ]


@router.get("/{shopper_id}/activity", response_model=PaginatedResponse[ShopperActivityEventResponse])
async def read_shopper_activity(
    merchant_id: UUID,
    shopper_id: UUID,
    limit: int = 50,
    offset: int = 0,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve paginated storefront activity events for drill-down investigation.
    """
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")

    result = await list_shopper_activity(
        session,
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        limit=limit,
        offset=offset,
        start_date=start_date,
        end_date=end_date,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Shopper not found")

    items, total = result
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)

