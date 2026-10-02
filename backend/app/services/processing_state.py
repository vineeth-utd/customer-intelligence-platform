import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.processing_state import (
    mark_processing_success,
    upsert_processing_state,
    get_eligible_entities
)
async def record_processing_failure(
    session: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
    target_type: str,
    error_message: str,
) -> None:
    """Records a failure state for a derived product.
    
    This updates the status to FAILED and stores the error message, but does 
    NOT advance last_generated_at. This ensures the entity remains eligible 
    for retry on the next scheduled run.
    """
    await upsert_processing_state(
        session,
        entity_type=entity_type,
        entity_id=entity_id,
        target_type=target_type,
        status="FAILED",
        error=error_message,
    )


async def record_processing_success(
    session: AsyncSession,
    entity_type: str,
    entity_id: uuid.UUID,
    target_type: str,
    generated_at: datetime,
) -> None:
    """Records successful generation of a derived product.
    
    This updates the status to SUCCESS and advances last_generated_at to the
    provided timestamp, preventing unnecessary regeneration until the underlying
    source data changes again.
    """
    await mark_processing_success(
        session,
        entity_type=entity_type,
        entity_id=entity_id,
        target_type=target_type,
        generated_at=generated_at,
    )


TARGET_DEPENDENCIES: dict[str, list[str]] = {
    # These are currently established minimal mappings for initial generation testing.
    # Complete dependencies should be finalized alongside each actual derived-product implementation.
    "merchant_profile": ["merchant", "shopper", "campaign"],
    "shopper_profile": ["shopper", "order"],
    "campaign_analytics": ["campaign", "shopper"],
}

async def get_eligible_entities_for_target(
    session: AsyncSession,
    entity_type: str,
    target_type: str,
    limit: int = 1000
) -> list[uuid.UUID]:
    """Get a batch of eligible entities for a given target."""
    dependencies = TARGET_DEPENDENCIES.get(target_type, [])
    if not dependencies:
        return []

    return await get_eligible_entities(
        session,
        entity_type=entity_type,
        target_type=target_type,
        depends_on_domains=dependencies,
        limit=limit
    )
