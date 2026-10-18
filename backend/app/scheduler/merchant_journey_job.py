import logging

from app.scheduler.incremental import process_incremental_target
from app.services.merchant_journey import generate_merchant_journeys_for_merchant

logger = logging.getLogger(__name__)


async def run_merchant_journey_job() -> None:
    """
    Scheduled job that drives incremental Merchant Journey generation.
    """
    logger.info("Starting incremental Merchant Journey generation job")
    try:
        await process_incremental_target(
            entity_type="merchant",
            target_type="merchant_journey",
            generator=generate_merchant_journeys_for_merchant,
            batch_size=100,
        )
    except Exception as e:
        logger.error("Error running merchant journey job", exc_info=e)
