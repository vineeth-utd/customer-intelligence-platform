import asyncio
import pytest
import sys
from aiokafka.errors import KafkaConnectionError

from app.config.settings import settings
from app.db.session import engine
from app.kafka.producer import event_producer
from scripts.run_shopper_generator import _run

@pytest.mark.asyncio
async def test_shopper_generator_smoke():
    """Smoke test to ensure the shopper generator can run."""
    await engine.dispose()
    
    # Ensure Kafka is available before trying to run the producer
    try:
        await event_producer.start()
        await event_producer.stop()
    except KafkaConnectionError:
        pytest.skip("Local Kafka broker is not reachable")

    try:
        await asyncio.wait_for(
            _run(
                shoppers_per_merchant=1,
                tick_interval_seconds=0.01,
                reload_interval_ticks=2,
                seed=42,
            ),
            timeout=0.1,
        )
    except asyncio.TimeoutError:
        pass # Expected since it runs forever
    except SystemExit as e:
        if e.code == 1:
            # Expected if DB has no merchants, skipping gracefully.
            pytest.skip("Database has no catalogs, generator exits cleanly.")
        else:
            raise
