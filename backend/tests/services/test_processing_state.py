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


@pytest.mark.asyncio
async def test_record_domain_activity_monotonic(session):
    from app.data_access.processing_state import record_domain_activity
    from app.models.processing_state import EntityDomainActivity
    
    entity_id = uuid.uuid4()
    base_time = datetime.now(timezone.utc)
    
    # 1. First activity
    await record_domain_activity(
        session,
        entity_type="merchant",
        entity_id=entity_id,
        domain="shopper",
        activity_timestamp=base_time,
    )
    
    stmt = select(EntityDomainActivity).where(
        EntityDomainActivity.entity_id == entity_id,
        EntityDomainActivity.domain == "shopper"
    ).execution_options(populate_existing=True)
    activity = (await session.execute(stmt)).scalar_one()
    assert activity.last_activity_at == base_time
    
    # 2. Older activity should not overwrite
    older_time = base_time - timedelta(minutes=5)
    await record_domain_activity(
        session,
        entity_type="merchant",
        entity_id=entity_id,
        domain="shopper",
        activity_timestamp=older_time,
    )
    
    activity = (await session.execute(stmt)).scalar_one()
    assert activity.last_activity_at == base_time
    
    # 3. Newer activity should overwrite
    newer_time = base_time + timedelta(minutes=5)
    await record_domain_activity(
        session,
        entity_type="merchant",
        entity_id=entity_id,
        domain="shopper",
        activity_timestamp=newer_time,
    )
    
    activity = (await session.execute(stmt)).scalar_one()
    assert activity.last_activity_at == newer_time


@pytest.mark.asyncio
async def test_get_eligible_entities_for_target(session):
    from app.data_access.processing_state import record_domain_activity
    from app.services.processing_state import get_eligible_entities_for_target
    
    merchant_id = uuid.uuid4()
    base_time = datetime.now(timezone.utc)
    
    # Insert a merchant so the base population query finds it
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from app.models.merchant import Merchant
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
    
    # Target: merchant_profile (depends on merchant, shopper, campaign)
    
    # Case 0: Entity exists but has NO processing state and NO activity -> Eligible
    eligible = await get_eligible_entities_for_target(
        session,
        entity_type="merchant",
        target_type="merchant_profile",
    )
    assert merchant_id in eligible
    
    # Case 1: Entity has activity but NO processing state -> Eligible
    await record_domain_activity(
        session,
        entity_type="merchant",
        entity_id=merchant_id,
        domain="shopper",
        activity_timestamp=base_time,
    )
    
    eligible = await get_eligible_entities_for_target(
        session,
        entity_type="merchant",
        target_type="merchant_profile",
    )
    assert merchant_id in eligible
    
    # Case 2: Entity has successful processing state NEWER than activity -> Not Eligible
    await record_processing_success(
        session,
        entity_type="merchant",
        entity_id=merchant_id,
        target_type="merchant_profile",
        generated_at=base_time + timedelta(minutes=5)
    )
    
    eligible = await get_eligible_entities_for_target(
        session,
        entity_type="merchant",
        target_type="merchant_profile",
    )
    assert merchant_id not in eligible
    
    # Case 3: Entity has new activity in a DIFFERENT domain it depends on -> Eligible
    await record_domain_activity(
        session,
        entity_type="merchant",
        entity_id=merchant_id,
        domain="campaign",
        activity_timestamp=base_time + timedelta(minutes=10),
    )
    
    eligible = await get_eligible_entities_for_target(
        session,
        entity_type="merchant",
        target_type="merchant_profile",
    )
    assert merchant_id in eligible
    
    # Case 4: Entity has failed processing state -> Eligible
    await record_processing_failure(
        session,
        entity_type="merchant",
        entity_id=merchant_id,
        target_type="merchant_profile",
        error_message="failed"
    )
    
    eligible = await get_eligible_entities_for_target(
        session,
        entity_type="merchant",
        target_type="merchant_profile",
    )
    assert merchant_id in eligible
