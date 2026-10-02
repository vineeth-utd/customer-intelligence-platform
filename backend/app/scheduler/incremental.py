import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.services.processing_state import (
    get_eligible_entities_for_target,
    record_processing_failure,
    record_processing_success,
)

logger = logging.getLogger(__name__)

# GeneratorCallback receives an active database session and the entity ID.
# It must use this session for its transactional work.
GeneratorCallback = Callable[[AsyncSession, uuid.UUID], Awaitable[None]]


async def process_incremental_target(
    entity_type: str,
    target_type: str,
    generator: GeneratorCallback,
    batch_size: int = 100,
) -> None:
    """
    Reusable workflow for generating derived products incrementally.
    
    Identifies eligible entities based on processing state and source activity,
    and invokes the provided generator callback for each.
    
    Failed entities are recorded but not retried in the same run to prevent
    infinite loops. Their state ensures they will be eligible for retry on
    the next scheduled run.
    """
    logger.info(f"Starting incremental job for {target_type}")
    
    processed_this_run: set[uuid.UUID] = set()
    
    while True:
        # 1. Identify eligible entities
        async with AsyncSessionLocal() as read_session:
            eligible_ids = await get_eligible_entities_for_target(
                read_session, entity_type, target_type, limit=batch_size
            )
            
        # Filter out entities we already attempted this run to prevent infinite loop
        # on failed entities (which remain eligible since their state doesn't advance)
        batch = [eid for eid in eligible_ids if eid not in processed_this_run]
        
        if not batch:
            break
            
        for entity_id in batch:
            processed_this_run.add(entity_id)
            
            # 2. Capture generation start time.
            # This is critical: if source activity occurs while generation is running,
            # that activity will have a timestamp > generation_start_time. Using this
            # pre-generation timestamp as the high-water mark ensures the entity becomes
            # eligible again to reflect the late-arriving activity.
            generation_start_time = datetime.now(timezone.utc)
            
            try:
                # 3. Process in isolation
                async with AsyncSessionLocal() as write_session:
                    await generator(write_session, entity_id)
                    
                    # Update processing state within the same transaction so it commits atomically
                    await record_processing_success(
                        write_session,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        target_type=target_type,
                        generated_at=generation_start_time,
                    )
                    await write_session.commit()
                    
            except Exception as e:
                logger.error(
                    f"Generation failed for {entity_type} {entity_id} target {target_type}",
                    exc_info=e
                )
                
                # 4. Record failure gracefully in a new transaction
                try:
                    async with AsyncSessionLocal() as failure_session:
                        await record_processing_failure(
                            failure_session,
                            entity_type=entity_type,
                            entity_id=entity_id,
                            target_type=target_type,
                            error_message=str(e),
                        )
                        await failure_session.commit()
                except Exception as secondary_error:
                    logger.critical(
                        f"Failed to record processing failure for {entity_id}",
                        exc_info=secondary_error
                    )
