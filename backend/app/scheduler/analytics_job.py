import logging
from datetime import date, datetime, timedelta, timezone

from app.db.session import AsyncSessionLocal
from app.services.analytics import generate_daily_metrics, refresh_aggregate_views
from app.config.settings import settings

logger = logging.getLogger(__name__)


async def run_analytics_job(
    start_date: date | None = None,
    end_date: date | None = None,
) -> None:
    """
    Executes the analytics pipeline:
    1. Recomputes daily metrics for the requested date range (or today and past lookback days).
       Dates are processed in ascending chronological order.
    2. Upon complete success, refreshes the aggregate materialized views.
    """
    logger.info("Starting analytics job")

    if start_date is not None and end_date is not None:
        if start_date > end_date:
            raise ValueError(f"start_date ({start_date}) must not be greater than end_date ({end_date})")
        dates_to_compute: list[date] = []
        curr = start_date
        while curr <= end_date:
            dates_to_compute.append(curr)
            curr += timedelta(days=1)
    elif start_date is not None or end_date is not None:
        raise ValueError("Both start_date and end_date must be provided for historical backfill")
    else:
        # Default scheduled behavior: past lookback days up to today in ascending order
        now_utc = datetime.now(timezone.utc)
        dates_to_compute = [
            (now_utc - timedelta(days=i)).date()
            for i in reversed(range(settings.analytics_job_lookback_days + 1))
        ]

    # 1. Generate daily metrics for each date independently in ascending order
    for metric_date in dates_to_compute:
        logger.info(f"Generating daily metrics for {metric_date}")
        try:
            async with AsyncSessionLocal() as session:
                await generate_daily_metrics(session, metric_date)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to generate daily metrics for {metric_date}", exc_info=e)
            # Abort the job gracefully. Do NOT refresh materialized views.
            raise

    # 2. Refresh materialized views after all generations succeed
    logger.info("Daily metrics generated successfully. Refreshing materialized views.")
    try:
        async with AsyncSessionLocal() as session:
            await refresh_aggregate_views(session)
        logger.info("Materialized views refreshed successfully.")
    except Exception as e:
        logger.error("Failed to refresh materialized views", exc_info=e)
        raise

    logger.info("Analytics job completed successfully")
