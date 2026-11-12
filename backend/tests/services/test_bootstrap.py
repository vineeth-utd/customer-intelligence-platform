"""Unit tests for historical derived processing bootstrap."""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.processing_state import record_domain_activity
from app.models.merchant import Merchant
from app.models.processing_state import EntityDomainActivity, EntityProcessingState
from app.models.shopper import Shopper
from app.services.bootstrap import run_historical_bootstrap
from app.services.processing_state import (
    TARGET_MERCHANT_HEALTH,
    TARGET_MERCHANT_JOURNEY,
    TARGET_MERCHANT_PROFILE,
    TARGET_SEGMENT_MEMBERSHIP,
    TARGET_SHOPPER_JOURNEY,
    TARGET_SHOPPER_PROFILE,
    get_eligible_entities_for_target,
)


@pytest.mark.asyncio
async def test_run_historical_bootstrap_executes_dependency_graph():
    start_date = date(2026, 9, 1)
    end_date = date(2026, 10, 31)
    as_of = datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc)

    merchant_id = uuid.uuid4()
    shopper_id = uuid.uuid4()

    mock_merchant = MagicMock()
    mock_merchant.merchant_id = merchant_id

    recorded_successes = []

    async def mock_record_success(session, entity_type, entity_id, target_type, generated_at):
        recorded_successes.append((entity_type, entity_id, target_type, generated_at))

    with (
        patch("app.services.bootstrap.verify_no_unprocessed_events", new_callable=AsyncMock) as mock_verify_events,
        patch("app.services.bootstrap.list_installed_merchants", new_callable=AsyncMock) as mock_list_merchants,
        patch("app.services.bootstrap.list_merchant_shoppers", new_callable=AsyncMock) as mock_list_shoppers,
        patch("app.services.bootstrap.initialize_merchant_segments", new_callable=AsyncMock) as mock_init_segments,
        patch("app.services.bootstrap.run_analytics_job", new_callable=AsyncMock) as mock_analytics_job,
        patch("app.services.bootstrap.generate_shopper_journeys_for_shopper", new_callable=AsyncMock) as mock_shopper_journey,
        patch("app.services.bootstrap.generate_merchant_journeys_for_merchant", new_callable=AsyncMock) as mock_merchant_journey,
        patch("app.services.bootstrap.generate_shopper_profile_callback", new_callable=AsyncMock) as mock_shopper_profile,
        patch("app.services.bootstrap.generate_merchant_profile_callback", new_callable=AsyncMock) as mock_merchant_profile,
        patch("app.services.bootstrap.refresh_shopper_segment_membership_callback", new_callable=AsyncMock) as mock_segment_refresh,
        patch("app.services.bootstrap.generate_merchant_health_callback", new_callable=AsyncMock) as mock_health,
        patch("app.services.bootstrap.record_processing_success", side_effect=mock_record_success),
        patch("app.services.bootstrap.AsyncSessionLocal") as mock_session_local,
    ):
        mock_verify_events.return_value = (True, {})
        mock_list_merchants.return_value = [mock_merchant]
        mock_list_shoppers.return_value = [shopper_id]
        mock_session_local.return_value.__aenter__.return_value = AsyncMock()

        await run_historical_bootstrap(start_date=start_date, end_date=end_date, as_of=as_of)

        # 1. Unprocessed event check
        assert mock_verify_events.called

        # 2. Segments initialized
        mock_init_segments.assert_called_once()

        # 3. Analytics range backfill
        mock_analytics_job.assert_called_once_with(start_date=start_date, end_date=end_date)

        # 4. Journeys
        mock_shopper_journey.assert_called_once_with(mock_session_local.return_value.__aenter__.return_value, shopper_id, as_of=as_of)
        mock_merchant_journey.assert_called_once_with(mock_session_local.return_value.__aenter__.return_value, merchant_id, as_of=as_of)

        # 5. Profiles
        mock_shopper_profile.assert_called_once_with(mock_session_local.return_value.__aenter__.return_value, shopper_id)
        mock_merchant_profile.assert_called_once_with(mock_session_local.return_value.__aenter__.return_value, merchant_id)

        # 6. Segment memberships
        mock_segment_refresh.assert_called_once_with(mock_session_local.return_value.__aenter__.return_value, shopper_id, as_of=as_of)

        # 7. Merchant Health
        mock_health.assert_called_once_with(mock_session_local.return_value.__aenter__.return_value, merchant_id, evaluation_time=as_of)

        # 8. All recorded processing states have last_generated_at == as_of and canonical target names
        assert len(recorded_successes) == 6
        target_types = {item[2] for item in recorded_successes}
        assert target_types == {
            TARGET_SHOPPER_JOURNEY,
            TARGET_MERCHANT_JOURNEY,
            TARGET_SHOPPER_PROFILE,
            TARGET_MERCHANT_PROFILE,
            TARGET_SEGMENT_MEMBERSHIP,
            TARGET_MERCHANT_HEALTH,
        }
        assert "journey" not in target_types
        assert "profile" not in target_types
        assert "segment" not in target_types
        for entity_type, entity_id, target_type, generated_at in recorded_successes:
            assert generated_at == as_of


@pytest.mark.asyncio
async def test_run_historical_bootstrap_fails_if_unprocessed_events_exist():
    start_date = date(2026, 9, 1)
    end_date = date(2026, 10, 31)

    with (
        patch("app.services.bootstrap.verify_no_unprocessed_events", new_callable=AsyncMock) as mock_verify_events,
        patch("app.services.bootstrap.AsyncSessionLocal") as mock_session_local,
    ):
        mock_verify_events.return_value = (False, {"merchant": 1})
        mock_session_local.return_value.__aenter__.return_value = AsyncMock()

        with pytest.raises(RuntimeError, match="unprocessed event rows exist"):
            await run_historical_bootstrap(start_date=start_date, end_date=end_date)


@pytest.mark.asyncio
async def test_historical_bootstrap_processing_state_canonical_targets_and_eligibility(db_session: AsyncSession):
    merchant_id = uuid.uuid4()
    shopper_id = uuid.uuid4()
    start_date = date(2026, 9, 1)
    end_date = date(2026, 10, 31)
    as_of = datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc)

    # Clean processing state for isolated testing
    await db_session.execute(delete(EntityProcessingState))
    await db_session.execute(delete(EntityDomainActivity))

    # Setup merchant and shopper
    await db_session.execute(
        pg_insert(Merchant).values(
            merchant_id=merchant_id,
            shopify_store_id=f"store-{merchant_id}",
            merchant_name="Bootstrap Test Merchant",
            email=f"merchant-{merchant_id}@example.com",
            country="US",
            timezone="UTC",
            store_currency="USD",
            app_install_status="installed",
        )
    )
    await db_session.execute(
        pg_insert(Shopper).values(
            shopper_id=shopper_id,
            merchant_id=merchant_id,
            email=f"shopper-{shopper_id}@example.com",
            first_seen_at=datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc),
            last_seen_at=datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc),
        )
    )
    # Record historical domain activity prior to as_of
    activity_ts = datetime(2026, 10, 25, 10, 0, 0, tzinfo=timezone.utc)
    for domain in ["merchant", "shopper", "campaign", "order", "product", "analytics"]:
        await record_domain_activity(db_session, "merchant", merchant_id, domain, activity_ts)
    for domain in ["shopper", "campaign", "order"]:
        await record_domain_activity(db_session, "shopper", shopper_id, domain, activity_ts)
    await db_session.commit()

    # Mock the callback actions in run_historical_bootstrap so we can run the real bootstrap flow
    with (
        patch("app.services.bootstrap.verify_no_unprocessed_events", new_callable=AsyncMock) as mock_verify,
        patch("app.services.bootstrap.initialize_merchant_segments", new_callable=AsyncMock),
        patch("app.services.bootstrap.run_analytics_job", new_callable=AsyncMock),
        patch("app.services.bootstrap.generate_shopper_journeys_for_shopper", new_callable=AsyncMock),
        patch("app.services.bootstrap.generate_merchant_journeys_for_merchant", new_callable=AsyncMock),
        patch("app.services.bootstrap.generate_shopper_profile_callback", new_callable=AsyncMock),
        patch("app.services.bootstrap.generate_merchant_profile_callback", new_callable=AsyncMock),
        patch("app.services.bootstrap.refresh_shopper_segment_membership_callback", new_callable=AsyncMock),
        patch("app.services.bootstrap.generate_merchant_health_callback", new_callable=AsyncMock),
    ):
        mock_verify.return_value = (True, {})
        await run_historical_bootstrap(start_date=start_date, end_date=end_date, as_of=as_of)

    # 1. Verify expected canonical EntityProcessingState rows exist
    stmt = select(EntityProcessingState).where(
        EntityProcessingState.entity_id.in_([merchant_id, shopper_id])
    )
    res = await db_session.execute(stmt)
    states = res.scalars().all()

    target_names = {s.target_type for s in states}
    expected_targets = {
        TARGET_SHOPPER_JOURNEY,
        TARGET_MERCHANT_JOURNEY,
        TARGET_SHOPPER_PROFILE,
        TARGET_MERCHANT_PROFILE,
        TARGET_SEGMENT_MEMBERSHIP,
        TARGET_MERCHANT_HEALTH,
    }
    assert expected_targets.issubset(target_names)

    # 2. Shorthand/incorrect target rows are NOT created
    assert "journey" not in target_names
    assert "profile" not in target_names
    assert "segment" not in target_names

    # Check watermarks
    for s in states:
        if s.target_type in expected_targets:
            assert s.last_generation_status == "SUCCESS"
            assert s.last_generated_at == as_of

    # 3. Immediately running eligibility checks finds NO entities stale solely because of target-name mismatch
    for target in [TARGET_SHOPPER_JOURNEY, TARGET_SHOPPER_PROFILE, TARGET_SEGMENT_MEMBERSHIP]:
        eligible = await get_eligible_entities_for_target(db_session, "shopper", target)
        assert shopper_id not in eligible

    for target in [TARGET_MERCHANT_JOURNEY, TARGET_MERCHANT_PROFILE, TARGET_MERCHANT_HEALTH]:
        eligible = await get_eligible_entities_for_target(db_session, "merchant", target)
        assert merchant_id not in eligible

    # 4. Genuinely newer LIVE source event makes the appropriate target eligible
    newer_ts = as_of + timedelta(hours=2)
    await record_domain_activity(db_session, "shopper", shopper_id, "shopper", newer_ts)
    await db_session.commit()

    # Shopper is now eligible for targets depending on "shopper"
    eligible_shopper_journeys = await get_eligible_entities_for_target(
        db_session, "shopper", TARGET_SHOPPER_JOURNEY
    )
    assert shopper_id in eligible_shopper_journeys

    eligible_shopper_profiles = await get_eligible_entities_for_target(
        db_session, "shopper", TARGET_SHOPPER_PROFILE
    )
    assert shopper_id in eligible_shopper_profiles

    # Merchant has no new activity newer than as_of -> remains NOT eligible
    eligible_merchants = await get_eligible_entities_for_target(
        db_session, "merchant", TARGET_MERCHANT_JOURNEY
    )
    assert merchant_id not in eligible_merchants

