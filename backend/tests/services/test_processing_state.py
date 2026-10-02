import uuid
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import select

from app.models.processing_state import EntityProcessingState
from app.services.processing_state import record_processing_success, record_processing_failure
from app.config.settings import settings
from app.db.session import AsyncSessionLocal, engine
from sqlalchemy import delete, text


@pytest.fixture
async def session():
    await engine.dispose()
    session = AsyncSessionLocal()
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        await session.close()
        pytest.skip(f"Local Postgres is not reachable: {exc}")

    await session.execute(delete(EntityProcessingState))
    await session.commit()

    yield session

    await session.execute(delete(EntityProcessingState))
    await session.commit()
    await session.close()


@pytest.mark.asyncio
async def test_record_processing_success(session):
    entity_id = uuid.uuid4()
    generated_at = datetime.now(timezone.utc)
    
    await record_processing_success(
        session,
        entity_type="shopper",
        entity_id=entity_id,
        target_type="profile",
        generated_at=generated_at,
    )
    
    stmt = select(EntityProcessingState).where(
        EntityProcessingState.entity_id == entity_id,
        EntityProcessingState.entity_type == "shopper",
        EntityProcessingState.target_type == "profile"
    ).execution_options(populate_existing=True)
    state = (await session.execute(stmt)).scalar_one()
    
    assert state.last_generation_status == "SUCCESS"
    assert state.last_error is None
    assert state.last_generated_at == generated_at

    # test update
    new_generated_at = generated_at + timedelta(minutes=5)
    await record_processing_success(
        session,
        entity_type="shopper",
        entity_id=entity_id,
        target_type="profile",
        generated_at=new_generated_at,
    )

    state = (await session.execute(stmt)).scalar_one()
    assert state.last_generation_status == "SUCCESS"
    assert state.last_error is None
    assert state.last_generated_at == new_generated_at


@pytest.mark.asyncio
async def test_record_processing_failure(session):
    entity_id = uuid.uuid4()
    
    await record_processing_failure(
        session,
        entity_type="merchant",
        entity_id=entity_id,
        target_type="health",
        error_message="Validation failed",
    )
    
    stmt = select(EntityProcessingState).where(
        EntityProcessingState.entity_id == entity_id,
        EntityProcessingState.entity_type == "merchant",
        EntityProcessingState.target_type == "health"
    ).execution_options(populate_existing=True)
    state = (await session.execute(stmt)).scalar_one()
    
    assert state.last_generation_status == "FAILED"
    assert state.last_error == "Validation failed"
    assert state.last_generated_at is None

    # update from success to failure should preserve last_generated_at
    generated_at = datetime.now(timezone.utc)
    await record_processing_success(
        session,
        entity_type="merchant",
        entity_id=entity_id,
        target_type="health",
        generated_at=generated_at,
    )

    await record_processing_failure(
        session,
        entity_type="merchant",
        entity_id=entity_id,
        target_type="health",
        error_message="Network error",
    )

    state = (await session.execute(stmt)).scalar_one()
    assert state.last_generation_status == "FAILED"
    assert state.last_error == "Network error"
    assert state.last_generated_at == generated_at
