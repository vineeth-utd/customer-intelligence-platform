import logging

from app.scheduler.incremental import process_incremental_target
from app.services.merchant_health import generate_merchant_health_callback

logger = logging.getLogger(__name__)


async def run_merchant_health_job() -> None:
    """
    Scheduled job that incrementally generates Merchant Health assessments
    for merchants whose operational state, profiles, journeys, or analytics have changed.
    """
    logger.info("Starting scheduled merchant health job")
    try:
        await process_incremental_target(
            entity_type="merchant",
            target_type="merchant_health",
            generator=generate_merchant_health_callback,
            batch_size=100,
        )
        logger.info("Merchant health job completed successfully")
    except Exception as e:
        logger.error("Failed during merchant health generation", exc_info=e)
        raise
