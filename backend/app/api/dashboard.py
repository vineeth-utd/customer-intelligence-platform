from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import (
    require_internal_principal,
    require_merchant_access,
)
from app.dependencies.db import get_db
from app.schemas.auth import Principal
from app.schemas.dashboard import (
    MerchantDashboardResponse,
    PlatformDashboardResponse,
)
from app.services.dashboard import (
    get_merchant_dashboard,
    get_platform_dashboard,
)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/platform", response_model=PlatformDashboardResponse)
async def read_platform_dashboard(
    start_date: date = Query(...),
    end_date: date = Query(...),
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_internal_principal),
):
    """
    Retrieve consolidated platform overview data (summary KPIs, metric trends, feature adoption).
    Requires INTERNAL platform access.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")

    return await get_platform_dashboard(session, start_date, end_date)


@router.get("/merchants/{merchant_id}", response_model=MerchantDashboardResponse)
async def read_merchant_dashboard(
    merchant_id: UUID,
    start_date: date = Query(...),
    end_date: date = Query(...),
    session: AsyncSession = Depends(get_db),
    _principal: Principal = Depends(require_merchant_access),
):
    """
    Retrieve consolidated merchant overview data (profile, health, KPIs, revenue, funnel,
    journeys, behavior, and campaigns) in a single request.
    Requires INTERNAL platform access or access scoped to the matching merchant.
    """
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date cannot be after end_date")

    result = await get_merchant_dashboard(session, merchant_id, start_date, end_date)
    if result is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return result

