import logging

from app.scheduler.incremental import process_incremental_target
from app.services.journey import generate_shopper_journeys_for_shopper

logger = logging.getLogger(__name__)


async def run_shopper_journey_job() -> None:
    """
    Scheduled job that drives incremental Shopper Journey generation.
    """
    logger.info("Starting incremental Shopper Journey generation job")
    try:
        await process_incremental_target(
            entity_type="shopper",
            target_type="shopper_journey",
            generator=generate_shopper_journeys_for_shopper,
            batch_size=100,
        )
    except Exception as e:
        logger.error("Error running shopper journey job", exc_info=e)
