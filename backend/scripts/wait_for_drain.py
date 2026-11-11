"""Standalone CLI tool to wait for Kafka consumers to drain topics into PostgreSQL.

Usage (from backend/):
    python scripts/wait_for_drain.py [--timeout 120] [--poll-interval 2.0]
"""

import argparse
import asyncio
import logging
import sys

from app.kafka.drain import wait_for_drain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Wait for Kafka consumer groups to drain event topics into PostgreSQL."
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Maximum seconds to wait before timing out (default: 120.0).",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="Polling interval in seconds between offset checks (default: 2.0).",
    )
    args = parser.parse_args()

    try:
        asyncio.run(wait_for_drain(timeout=args.timeout, poll_interval=args.poll_interval))
        logger.info("Kafka consumer drain verified successfully.")
    except Exception as e:
        logger.error("Consumer drain failed or timed out: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()

