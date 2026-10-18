import logging

from app.scheduler.incremental import process_incremental_target
from app.services.segment import refresh_shopper_segment_membership_callback

logger = logging.getLogger(__name__)


async def run_shopper_segment_membership_job() -> None:
    """
    Scheduled job that incrementally refreshes Shopper Segment Membership
    for shoppers whose source operational data, profiles, or journeys have changed.
    """
    logger.info("Starting scheduled shopper segment membership job")
    try:
        await process_incremental_target(
            entity_type="shopper",
            target_type="segment_membership",
            generator=refresh_shopper_segment_membership_callback,
            batch_size=100,
        )
        logger.info("Shopper segment membership job completed successfully")
    except Exception as e:
        logger.error("Failed during shopper segment membership generation", exc_info=e)
        raise
