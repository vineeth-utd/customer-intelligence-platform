import argparse
import asyncio
from datetime import date
import logging

from app.scheduler.analytics_job import run_analytics_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger analytics job (daily metrics and materialized views)")
    parser.add_argument(
        "--start-date",
        type=lambda s: date.fromisoformat(s),
        help="Start date for backfill (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=lambda s: date.fromisoformat(s),
        help="End date for backfill (YYYY-MM-DD)",
    )
    args = parser.parse_args()

    if (args.start_date is None) != (args.end_date is None):
        parser.error("Both --start-date and --end-date must be provided together")

    if args.start_date and args.end_date:
        logger.info(f"Triggering analytics backfill from {args.start_date} to {args.end_date}")
    else:
        logger.info("Triggering scheduled analytics job execution (lookback window)")

    try:
        await run_analytics_job(start_date=args.start_date, end_date=args.end_date)
        logger.info("Analytics job completed successfully.")
    except Exception as e:
        logger.error("Analytics job execution failed.", exc_info=e)
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
