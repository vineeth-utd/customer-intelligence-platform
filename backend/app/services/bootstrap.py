from datetime import date, datetime, timezone
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.merchant import list_installed_merchants
from app.data_access.shopper import list_merchant_shoppers
from app.db.session import AsyncSessionLocal
from app.kafka.drain import verify_no_unprocessed_events
from app.scheduler.analytics_job import run_analytics_job
from app.services.journey import generate_shopper_journeys_for_shopper
from app.services.merchant_health import generate_merchant_health_callback
from app.services.merchant_journey import generate_merchant_journeys_for_merchant
from app.services.processing_state import record_processing_success
from app.services.profile import (
    generate_merchant_profile_callback,
    generate_shopper_profile_callback,
)
from app.services.segment import (
    initialize_merchant_segments,
    refresh_shopper_segment_membership_callback,
)

logger = logging.getLogger(__name__)


async def run_historical_bootstrap(
    start_date: date,
    end_date: date,
    as_of: datetime | None = None,
) -> None:
    """Execute authoritative historical derived-product bootstrap.

    Follows the strict derived dependency graph:
    1. Verify operational ingestion complete (no failed/unprocessed event records).
    2. Initialize canonical shopper segments for installed merchants.
    3. Analytics Range Backfill: recompute daily metrics across [start_date, end_date]
       in ascending chronological order, followed by aggregate materialized-view refresh.
    4. Journeys & Profiles:
       - Shopper Journeys & Merchant Journeys as of as_of.
       - Shopper Profiles & Merchant Profiles (operational aggregations).
    5. Shopper Segment Memberships:
       - Evaluated after Shopper Profiles and Shopper Journeys as of as_of.
    6. Merchant Health:
       - Evaluated after Analytics, Merchant Profiles, and Merchant Journeys as of as_of.
    7. Processing State Watermarks:
       - Record EntityProcessingState.last_generated_at = as_of for each target type.
    """
    if as_of is None:
        as_of = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
    elif as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)

    logger.info(
        "Starting historical bootstrap for range [%s, %s] as of %s",
        start_date,
        end_date,
        as_of.isoformat(),
    )

    # 1. Verify operational ingestion complete
    async with AsyncSessionLocal() as session:
        is_clean, unprocessed = await verify_no_unprocessed_events(session)
        if not is_clean:
            raise RuntimeError(
                f"Cannot bootstrap historical dataset: unprocessed event rows exist: {unprocessed}"
            )

        merchants = await list_installed_merchants(session)
        if not merchants:
            logger.warning("No installed merchants found in operational database. Nothing to bootstrap.")
            return

        # 2. Ensure canonical shopper segments exist for each installed merchant
        for m in merchants:
            await initialize_merchant_segments(session, m.merchant_id)
        await session.commit()

        # Collect all shopper IDs
        all_shopper_ids: list[tuple[uuid.UUID, uuid.UUID]] = [] # (shopper_id, merchant_id)
        for m in merchants:
            shoppers = await list_merchant_shoppers(session, m.merchant_id)
            for s_id in shoppers:
                all_shopper_ids.append((s_id, m.merchant_id))

    # 3. Analytics Range Backfill & Materialized View Refresh
    logger.info("Executing analytics range backfill from %s to %s...", start_date, end_date)
    await run_analytics_job(start_date=start_date, end_date=end_date)
    logger.info("Analytics range backfill and materialized views refreshed.")

    # 4. Journeys and Profiles
    logger.info("Generating Shopper & Merchant Journeys as of %s...", as_of.isoformat())
    async with AsyncSessionLocal() as session:
        for shopper_id, _m_id in all_shopper_ids:
            await generate_shopper_journeys_for_shopper(session, shopper_id, as_of=as_of)
            await record_processing_success(session, "shopper", shopper_id, "journey", as_of)

        for m in merchants:
            await generate_merchant_journeys_for_merchant(session, m.merchant_id, as_of=as_of)
            await record_processing_success(session, "merchant", m.merchant_id, "journey", as_of)
        await session.commit()

    logger.info("Generating Shopper & Merchant Profiles...")
    async with AsyncSessionLocal() as session:
        for shopper_id, _m_id in all_shopper_ids:
            await generate_shopper_profile_callback(session, shopper_id)
            await record_processing_success(session, "shopper", shopper_id, "profile", as_of)

        for m in merchants:
            await generate_merchant_profile_callback(session, m.merchant_id)
            await record_processing_success(session, "merchant", m.merchant_id, "profile", as_of)
        await session.commit()

    # 5. Shopper Segment Membership (depends on Shopper Profiles + Shopper Journeys)
    logger.info("Evaluating Shopper Segment Memberships as of %s...", as_of.isoformat())
    async with AsyncSessionLocal() as session:
        for shopper_id, _m_id in all_shopper_ids:
            await refresh_shopper_segment_membership_callback(session, shopper_id, as_of=as_of)
            await record_processing_success(session, "shopper", shopper_id, "segment", as_of)
        await session.commit()

    # 6. Merchant Health (depends on Analytics + Merchant Profiles + Merchant Journeys)
    logger.info("Calculating Merchant Health scores as of %s...", as_of.isoformat())
    async with AsyncSessionLocal() as session:
        for m in merchants:
            await generate_merchant_health_callback(session, m.merchant_id, evaluation_time=as_of)
            await record_processing_success(session, "merchant", m.merchant_id, "merchant_health", as_of)
        await session.commit()

    logger.info("Historical bootstrap completed successfully as of %s.", as_of.isoformat())

