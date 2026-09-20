"""Standalone entrypoint for the campaign event Kafka consumer.

Runs independently of the FastAPI app: starts the campaign event consumer,
which validates and idempotently persists each Campaign event into the
campaign_events table (intermediate persistence-only mode for Unit 3.7C).

Usage (from backend/):
    uv run python -m scripts.run_campaign_event_consumer
"""

import asyncio
import logging

from app.kafka.consumer import campaign_event_consumer

logger = logging.getLogger(__name__)


async def _run() -> None:
    await campaign_event_consumer.start()
    try:
        await campaign_event_consumer.run_forever()
    finally:
        await campaign_event_consumer.stop()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        logger.info("Campaign event consumer stopped by user")


if __name__ == "__main__":
    main()
