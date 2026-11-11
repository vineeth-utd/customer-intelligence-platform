"""Standalone CLI script to execute historical derived-product bootstrap.

Usage (from backend/):
    python scripts/bootstrap_historical.py --start-date 2026-09-01 --end-date 2026-11-01 [--as-of 2026-11-01T23:59:59Z]
"""

import argparse
import asyncio
from datetime import date, datetime, timezone
import logging
import sys

from app.services.bootstrap import run_historical_bootstrap

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bootstrap historical derived intelligence and analytics for the Customer Intelligence Platform."
    )
    parser.add_argument(
        "--start-date",
        type=lambda s: date.fromisoformat(s),
        required=True,
        help="Start date of the historical simulation period (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end-date",
        type=lambda s: date.fromisoformat(s),
        required=True,
        help="End date of the historical simulation period (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--as-of",
        type=lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")),
        default=None,
        help="Optional ISO datetime to evaluate time-window models as of (defaults to end of end_date).",
    )
    args = parser.parse_args()

    if args.start_date > args.end_date:
        parser.error(f"--start-date ({args.start_date}) cannot be greater than --end-date ({args.end_date})")

    try:
        asyncio.run(
            run_historical_bootstrap(
                start_date=args.start_date,
                end_date=args.end_date,
                as_of=args.as_of,
            )
        )
        logger.info("Historical bootstrap execution completed successfully.")
    except Exception as e:
        logger.error("Historical bootstrap execution failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

