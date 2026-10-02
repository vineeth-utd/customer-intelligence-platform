import uuid
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.merchant import Merchant
from app.models.processing_state import EntityProcessingState
from app.scheduler.incremental import process_incremental_target
from app.data_access.processing_state import record_domain_activity

from app.db.session import AsyncSessionLocal, engine
from sqlalchemy import text

class DummyGeneratorError(Exception):
    """Exception used for testing failures."""
    pass


@pytest.fixture
async def session():
    await engine.dispose()
    session = AsyncSessionLocal()
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        await session.close()
        raise exc
    yield session
    await session.rollback()
    await session.close()


@pytest.mark.asyncio
async def test_process_incremental_target_success(session):
    """Test that a successful generation advances processing state correctly."""
    merchant_id = uuid.uuid4()
    base_time = datetime.now(timezone.utc)
    
    # 1. Setup base entity and domain activity to make it eligible
    await session.execute(
        pg_insert(Merchant).values(
            merchant_id=merchant_id,
            shopify_store_id=f"store-{merchant_id}",
            merchant_name="Test Merchant",
            email="test@merchant.com",
            country="US",
            timezone="UTC",
            store_currency="USD",
            app_install_status="installed",
        )
    )
    await record_domain_activity(
        session, "merchant", merchant_id, "merchant", base_time
    )
    # Commit so the new sessions created by orchestrator can see it
    await session.commit()
    
    # 2. Mock generator that tracks execution
    executed_for = []
    
    async def mock_generator(s: AsyncSession, eid: uuid.UUID) -> None:
        executed_for.append(eid)
        # Verify it gets a valid session
        assert s is not None
        
    # 3. Run incremental processor
    await process_incremental_target(
        entity_type="merchant",
        target_type="merchant_profile",
        generator=mock_generator,
        batch_size=10
    )
    
    # Verify generator ran exactly once for this entity
    assert merchant_id in executed_for
    
    # 4. Verify state advanced correctly
    from sqlalchemy import select
    from app.models.processing_state import EntityProcessingState
    
    # Use the test session to verify (it might need a refresh/select)
    stmt = select(EntityProcessingState).where(
        EntityProcessingState.entity_type == "merchant",
        EntityProcessingState.entity_id == merchant_id,
        EntityProcessingState.target_type == "merchant_profile",
    )
    state = (await session.execute(stmt)).scalar_one_or_none()
    
    assert state is not None
    assert state.last_generation_status == "SUCCESS"
    assert state.last_error is None
    # Generated time should be >= the base time we used
    assert state.last_generated_at >= base_time


@pytest.mark.asyncio
async def test_process_incremental_target_failure(session):
    """Test that a failure in generation is recorded safely and isolated."""
    merchant_id = uuid.uuid4()
    base_time = datetime.now(timezone.utc)
    
    # 1. Setup base entity and domain activity to make it eligible
    await session.execute(
        pg_insert(Merchant).values(
            merchant_id=merchant_id,
            shopify_store_id=f"store-{merchant_id}-fail",
            merchant_name="Fail Merchant",
            email="fail@merchant.com",
            country="US",
            timezone="UTC",
            store_currency="USD",
            app_install_status="installed",
        )
    )
    await record_domain_activity(
        session, "merchant", merchant_id, "merchant", base_time
    )
    await session.commit()
    
    # 2. Mock generator that fails
    attempts = 0
    
    async def failing_generator(s: AsyncSession, eid: uuid.UUID) -> None:
        nonlocal attempts
        attempts += 1
        raise DummyGeneratorError("Simulated failure")
        
    # 3. Run incremental processor
    await process_incremental_target(
        entity_type="merchant",
        target_type="merchant_profile",
        generator=failing_generator,
        batch_size=10
    )
    
    # Verify it was only attempted ONCE in this run (no infinite loop)
    assert attempts == 1
    
    # 4. Verify state recorded failure but did not advance timestamp
    from sqlalchemy import select
    
    stmt = select(EntityProcessingState).where(
        EntityProcessingState.entity_type == "merchant",
        EntityProcessingState.entity_id == merchant_id,
        EntityProcessingState.target_type == "merchant_profile",
    )
    state = (await session.execute(stmt)).scalar_one_or_none()
    
    assert state is not None
    assert state.last_generation_status == "FAILED"
    assert state.last_error == "Simulated failure"
    assert state.last_generated_at is None  # Timestamp shouldn't advance on failure
