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
        if eid == merchant_id:
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


@pytest.mark.asyncio
async def test_process_incremental_concurrent_activity(session):
    """Test that source activity arriving during generation keeps the entity eligible."""
    from app.services.processing_state import get_eligible_entities_for_target
    import asyncio
    
    merchant_id = uuid.uuid4()
    base_time = datetime.now(timezone.utc)
    
    # 1. Setup base entity
    await session.execute(
        pg_insert(Merchant).values(
            merchant_id=merchant_id,
            shopify_store_id=f"store-{merchant_id}-concurrent",
            merchant_name="Concurrent Merchant",
            email="concurrent@merchant.com",
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
    
    # 2. Mock generator that simulates concurrent activity during execution
    async def concurrent_generator(s: AsyncSession, eid: uuid.UUID) -> None:
        # Simulate some delay
        await asyncio.sleep(0.1)
        
        # Simulate new activity arriving AFTER the generation started (in a separate transaction context)
        # Using the test's main session fixture which is isolated from the generator's session
        newer_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        
        # We need a new session since we are simulating an independent Kafka worker
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as concurrent_session:
            await record_domain_activity(
                concurrent_session, "merchant", eid, "merchant", newer_time
            )
            await concurrent_session.commit()
            
    # 3. Run incremental processor
    await process_incremental_target(
        entity_type="merchant",
        target_type="merchant_profile",
        generator=concurrent_generator,
        batch_size=10
    )
    
    # 4. Verify entity is still eligible because concurrent activity > generation_start_time
    eligible_ids = await get_eligible_entities_for_target(
        session, "merchant", "merchant_profile"
    )
    
    assert merchant_id in eligible_ids


@pytest.mark.asyncio
async def test_process_incremental_batch_isolation(session):
    """Test that one entity's failure does not prevent siblings from succeeding."""
    merchant_id_fail = uuid.uuid4()
    merchant_id_success = uuid.uuid4()
    base_time = datetime.now(timezone.utc)
    
    # 1. Setup both entities
    await session.execute(
        pg_insert(Merchant).values([
            {
                "merchant_id": merchant_id_fail,
                "shopify_store_id": f"store-{merchant_id_fail}",
                "merchant_name": "Fail Merchant",
                "email": "fail@merchant.com",
                "country": "US",
                "timezone": "UTC",
                "store_currency": "USD",
                "app_install_status": "installed",
            },
            {
                "merchant_id": merchant_id_success,
                "shopify_store_id": f"store-{merchant_id_success}",
                "merchant_name": "Success Merchant",
                "email": "success@merchant.com",
                "country": "US",
                "timezone": "UTC",
                "store_currency": "USD",
                "app_install_status": "installed",
            }
        ])
    )
    await record_domain_activity(
        session, "merchant", merchant_id_fail, "merchant", base_time
    )
    await record_domain_activity(
        session, "merchant", merchant_id_success, "merchant", base_time
    )
    await session.commit()
    
    # 2. Mock generator that fails for one, succeeds for the other
    async def mixed_generator(s: AsyncSession, eid: uuid.UUID) -> None:
        if eid == merchant_id_fail:
            raise DummyGeneratorError("Simulated failure for one entity")
        # Else succeeds
            
    # 3. Run incremental processor
    await process_incremental_target(
        entity_type="merchant",
        target_type="merchant_profile",
        generator=mixed_generator,
        batch_size=10
    )
    
    # 4. Verify states
    from sqlalchemy import select
    
    stmt_fail = select(EntityProcessingState).where(
        EntityProcessingState.entity_id == merchant_id_fail
    )
    state_fail = (await session.execute(stmt_fail)).scalar_one_or_none()
    
    assert state_fail is not None
    assert state_fail.last_generation_status == "FAILED"
    assert state_fail.last_error == "Simulated failure for one entity"
    
    stmt_success = select(EntityProcessingState).where(
        EntityProcessingState.entity_id == merchant_id_success
    )
    state_success = (await session.execute(stmt_success)).scalar_one_or_none()
    
    assert state_success is not None
    assert state_success.last_generation_status == "SUCCESS"
    assert state_success.last_error is None
