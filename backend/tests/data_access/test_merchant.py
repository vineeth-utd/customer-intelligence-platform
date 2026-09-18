"""Integration test against a live local Postgres for plan/feature reference-data persistence.

Requires `docker-compose up postgres` running locally. Skips itself if the
database is unreachable, mirroring tests/data_access/test_merchant_events.py.
"""

import pytest
from sqlalchemy import delete, text

from app.config.settings import settings
from app.data_access.merchant import get_feature_by_key, get_plan_by_key, upsert_feature, upsert_plan
from app.db.session import AsyncSessionLocal, engine
from app.models.merchant import PlatformFeature, SubscriptionPlan
from app.reference_data.features import FeatureCatalogEntry, FeatureKey
from app.reference_data.plans import PlanCatalogEntry, PlanKey


@pytest.fixture
async def db_session():
    # Each async test runs on its own event loop, but the engine's connection
    # pool is a module-level singleton - dispose it first so a stale
    # connection bound to a previous test's loop is never reused here.
    await engine.dispose()

    session = AsyncSessionLocal()
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        await session.close()
        pytest.skip(f"Local Postgres is not reachable at {settings.postgres_host}:{settings.postgres_port}: {exc}")
    yield session
    await session.close()


async def _delete_plan(session, plan_key: PlanKey) -> None:
    await session.execute(delete(SubscriptionPlan).where(SubscriptionPlan.plan_key == plan_key.value))
    await session.commit()


async def _delete_feature(session, feature_key: FeatureKey) -> None:
    await session.execute(delete(PlatformFeature).where(PlatformFeature.feature_key == feature_key.value))
    await session.commit()


async def test_upsert_plan_inserts_then_updates_on_conflict(db_session):
    await _delete_plan(db_session, PlanKey.STARTER)
    try:
        entry = PlanCatalogEntry(plan_key=PlanKey.STARTER, plan_name="Starter", monthly_price=19, annual_price=190)
        await upsert_plan(db_session, entry)
        await db_session.commit()

        plan = await get_plan_by_key(db_session, PlanKey.STARTER)
        assert plan is not None
        assert plan.plan_name == "Starter"
        assert float(plan.monthly_price) == 19

        changed_entry = PlanCatalogEntry(
            plan_key=PlanKey.STARTER, plan_name="Starter Renamed", monthly_price=25, annual_price=250
        )
        await upsert_plan(db_session, changed_entry)
        await db_session.commit()

        refreshed = await get_plan_by_key(db_session, PlanKey.STARTER)
        assert refreshed.plan_name == "Starter Renamed"
        assert float(refreshed.monthly_price) == 25
    finally:
        await _delete_plan(db_session, PlanKey.STARTER)


async def test_upsert_feature_inserts_then_updates_on_conflict(db_session):
    await _delete_feature(db_session, FeatureKey.WISHLIST)
    try:
        entry = FeatureCatalogEntry(
            feature_key=FeatureKey.WISHLIST, feature_name="Wishlist", feature_category="shopper_engagement"
        )
        await upsert_feature(db_session, entry)
        await db_session.commit()

        feature = await get_feature_by_key(db_session, FeatureKey.WISHLIST)
        assert feature is not None
        assert feature.feature_name == "Wishlist"

        changed_entry = FeatureCatalogEntry(
            feature_key=FeatureKey.WISHLIST, feature_name="Wishlist Renamed", feature_category="shopper_engagement"
        )
        await upsert_feature(db_session, changed_entry)
        await db_session.commit()

        refreshed = await get_feature_by_key(db_session, FeatureKey.WISHLIST)
        assert refreshed.feature_name == "Wishlist Renamed"
    finally:
        await _delete_feature(db_session, FeatureKey.WISHLIST)


async def test_get_plan_by_key_returns_none_when_not_seeded(db_session):
    await _delete_plan(db_session, PlanKey.PREMIUM)
    assert await get_plan_by_key(db_session, PlanKey.PREMIUM) is None


async def test_get_feature_by_key_returns_none_when_not_seeded(db_session):
    await _delete_feature(db_session, FeatureKey.META_PIXEL)
    assert await get_feature_by_key(db_session, FeatureKey.META_PIXEL) is None


async def test_upsert_plan_does_not_commit(db_session):
    await _delete_plan(db_session, PlanKey.GROWTH)
    try:
        entry = PlanCatalogEntry(plan_key=PlanKey.GROWTH, plan_name="Growth", monthly_price=199, annual_price=1990)
        await upsert_plan(db_session, entry)
        await db_session.rollback()

        async with AsyncSessionLocal() as other_session:
            assert await get_plan_by_key(other_session, PlanKey.GROWTH) is None
    finally:
        await _delete_plan(db_session, PlanKey.GROWTH)
