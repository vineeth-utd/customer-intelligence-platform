import asyncio
import logging

from app.kafka.consumer import shopper_event_consumer
from app.kafka.producer import event_producer

logger = logging.getLogger(__name__)

async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting shopper event consumer...")

    await event_producer.start()

    try:
        await shopper_event_consumer.start()

        try:
            logger.info("Shopper event consumer started. Listening for messages...")
            await shopper_event_consumer.run_forever()
        except asyncio.CancelledError:
            logger.info("Consumer loop cancelled")
        finally:
            await shopper_event_consumer.stop()
            logger.info("Shopper event consumer stopped")
    finally:
        await event_producer.stop()

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
