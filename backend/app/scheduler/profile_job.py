import logging
from app.scheduler.incremental import process_incremental_target
from app.services.profile import (
    generate_merchant_profile_callback,
    generate_shopper_profile_callback
)

logger = logging.getLogger(__name__)

async def run_merchant_profile_job() -> None:
    """
    Scheduled job that incrementally generates Merchant Profiles
    for merchants whose source operational data has changed.
    """
    logger.info("Starting scheduled merchant profile job")
    
    try:
        await process_incremental_target(
            entity_type="merchant",
            target_type="merchant_profile",
            generator=generate_merchant_profile_callback,
            batch_size=100
        )
        logger.info("Merchant profile job completed successfully")
    except Exception as e:
        logger.error("Failed during merchant profile generation", exc_info=e)
        raise

async def run_shopper_profile_job() -> None:
    """
    Scheduled job that incrementally generates Shopper Profiles
    for shoppers whose source operational data has changed.
    """
    logger.info("Starting scheduled shopper profile job")
    
    try:
        await process_incremental_target(
            entity_type="shopper",
            target_type="shopper_profile",
            generator=generate_shopper_profile_callback,
            batch_size=100
        )
        logger.info("Shopper profile job completed successfully")
    except Exception as e:
        logger.error("Failed during shopper profile generation", exc_info=e)
        raise
