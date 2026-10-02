import uuid
from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.processing_state import EntityProcessingState, EntityDomainActivity
from app.models.merchant import Merchant
from app.models.shopper import Shopper
from app.models.campaign import Campaign


async def upsert_processing_state(
    session: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
    target_type: str,
    status: str,
    error: str | None = None
) -> None:
    """Upsert a processing state record without updating last_generated_at."""
    stmt = (
        pg_insert(EntityProcessingState)
        .values(
            entity_type=entity_type,
            entity_id=entity_id,
            target_type=target_type,
            last_generation_status=status,
            last_error=error,
        )
        .on_conflict_do_update(
            index_elements=["entity_type", "entity_id", "target_type"],
            set_={
                "last_generation_status": status,
                "last_error": error,
            }
        )
    )
    await session.execute(stmt)


async def mark_processing_success(
    session: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
    target_type: str,
    generated_at: datetime,
) -> None:
    """Update processing state upon successful generation, advancing last_generated_at."""
    stmt = (
        pg_insert(EntityProcessingState)
        .values(
            entity_type=entity_type,
            entity_id=entity_id,
            target_type=target_type,
            last_generated_at=generated_at,
            last_generation_status="SUCCESS",
            last_error=None,
        )
        .on_conflict_do_update(
            index_elements=["entity_type", "entity_id", "target_type"],
            set_={
                "last_generated_at": generated_at,
                "last_generation_status": "SUCCESS",
                "last_error": None,
            }
        )
    )
    await session.execute(stmt)


async def record_domain_activity(
    session: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
    domain: str,
    activity_timestamp: datetime,
) -> None:
    """Record source domain activity using an optimized UPSERT."""
    stmt = (
        pg_insert(EntityDomainActivity)
        .values(
            entity_type=entity_type,
            entity_id=entity_id,
            domain=domain,
            last_activity_at=activity_timestamp,
        )
        .on_conflict_do_update(
            index_elements=["entity_type", "entity_id", "domain"],
            set_={"last_activity_at": activity_timestamp},
            where=(EntityDomainActivity.last_activity_at < activity_timestamp)
        )
    )
    await session.execute(stmt)


async def get_eligible_entities(
    session: AsyncSession,
    entity_type: str,
    target_type: str,
    depends_on_domains: list[str],
    limit: int = 1000,
) -> list[uuid.UUID]:
    """
    Get a batch of entity IDs eligible for regeneration for a specific target.
    An entity is eligible if its target processing state is missing/failed, or if 
    any of its required source domains have activity newer than its last_generated_at.
    """
    if entity_type == "merchant":
        base_model = Merchant
        base_id_col = Merchant.merchant_id
    elif entity_type == "shopper":
        base_model = Shopper
        base_id_col = Shopper.shopper_id
    elif entity_type == "campaign":
        base_model = Campaign
        base_id_col = Campaign.campaign_id
    else:
        raise ValueError(f"Unknown entity_type for eligibility: {entity_type}")

    stmt = select(base_id_col).outerjoin(
        EntityProcessingState,
        and_(
            EntityProcessingState.entity_type == entity_type,
            EntityProcessingState.entity_id == base_id_col,
            EntityProcessingState.target_type == target_type
        )
    ).outerjoin(
        EntityDomainActivity,
        and_(
            EntityDomainActivity.entity_type == entity_type,
            EntityDomainActivity.entity_id == base_id_col,
            EntityDomainActivity.domain.in_(depends_on_domains)
        )
    ).where(
        or_(
            EntityProcessingState.last_generated_at.is_(None),
            EntityProcessingState.last_generation_status == "FAILED",
            EntityDomainActivity.last_activity_at > EntityProcessingState.last_generated_at
        )
    ).distinct().limit(limit)
    
    result = await session.execute(stmt)
    return list(result.scalars().all())
