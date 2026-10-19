import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.merchant_health import MerchantHealth


async def upsert_merchant_health(
    session: AsyncSession,
    *,
    merchant_id: uuid.UUID,
    health_score: float,
    health_status: str,
    churn_risk_score: float,
    engagement_score: float,
    feature_adoption_score: float,
    business_performance_score: float,
    calculated_at: datetime,
) -> None:
    """
    Inserts or updates the MerchantHealth derived record for a merchant.
    Single-transaction idempotent persistence.
    """
    stmt = (
        pg_insert(MerchantHealth)
        .values(
            merchant_id=merchant_id,
            health_score=health_score,
            health_status=health_status,
            churn_risk_score=churn_risk_score,
            engagement_score=engagement_score,
            feature_adoption_score=feature_adoption_score,
            business_performance_score=business_performance_score,
            calculated_at=calculated_at,
        )
        .on_conflict_do_update(
            index_elements=["merchant_id"],
            set_={
                "health_score": health_score,
                "health_status": health_status,
                "churn_risk_score": churn_risk_score,
                "engagement_score": engagement_score,
                "feature_adoption_score": feature_adoption_score,
                "business_performance_score": business_performance_score,
                "calculated_at": calculated_at,
            },
        )
    )
    await session.execute(stmt)


async def get_merchant_health(
    session: AsyncSession, merchant_id: uuid.UUID
) -> MerchantHealth | None:
    """Retrieve the current health assessment for a merchant."""
    stmt = select(MerchantHealth).where(MerchantHealth.merchant_id == merchant_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_merchant_health_paginated(
    session: AsyncSession,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[Sequence[MerchantHealth], int]:
    """
    Retrieve merchant health assessments with deterministic ordering and optional status filtering.
    Orders by health_score ASC so at-risk merchants appear first.
    """
    count_stmt = select(func.count(MerchantHealth.merchant_id))
    if status_filter:
        count_stmt = count_stmt.where(MerchantHealth.health_status == status_filter)
    total_count = (await session.execute(count_stmt)).scalar() or 0

    stmt = select(MerchantHealth)
    if status_filter:
        stmt = stmt.where(MerchantHealth.health_status == status_filter)
    stmt = stmt.order_by(MerchantHealth.health_score.asc(), MerchantHealth.merchant_id.asc()).limit(limit).offset(offset)

    result = await session.execute(stmt)
    return result.scalars().all(), total_count
