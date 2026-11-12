"""Integration test against a live local Postgres for merchant reference-data initialization.

Requires `docker-compose up postgres` running locally. Skips itself if the
database is unreachable, mirroring tests/data_access/test_merchant_events.py.
"""

import pytest
from sqlalchemy import delete, func, select, text

from app.config.settings import settings
from app.models.merchant import PlatformFeature, SubscriptionPlan, PlanFeature, FeatureEventMapping
from app.models.metrics import FeatureMetricsDaily
from app.reference_data.features import FEATURE_CATALOG
from app.reference_data.plans import PLAN_CATALOG
from app.services.merchant import initialize_reference_data


@pytest.fixture
async def db_session(test_session_factory):
    async with test_session_factory() as session:
        await session.execute(delete(PlanFeature))
        await session.execute(delete(FeatureEventMapping))
        await session.execute(delete(SubscriptionPlan))
        await session.execute(delete(FeatureMetricsDaily))
        await session.execute(delete(PlatformFeature))
        await session.commit()

        yield session

        await initialize_reference_data(session)


async def test_initialize_reference_data_seeds_the_full_catalog(db_session):
    await initialize_reference_data(db_session)

    plan_count = await db_session.scalar(select(func.count()).select_from(SubscriptionPlan))
    feature_count = await db_session.scalar(select(func.count()).select_from(PlatformFeature))
    assert plan_count == len(PLAN_CATALOG)
    assert feature_count == len(FEATURE_CATALOG)


async def test_initialize_reference_data_is_idempotent(db_session):
    await initialize_reference_data(db_session)
    await initialize_reference_data(db_session)

    plan_count = await db_session.scalar(select(func.count()).select_from(SubscriptionPlan))
    feature_count = await db_session.scalar(select(func.count()).select_from(PlatformFeature))
    assert plan_count == len(PLAN_CATALOG)
    assert feature_count == len(FEATURE_CATALOG)
