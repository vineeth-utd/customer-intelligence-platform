"""Unit tests for historical derived processing bootstrap."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.services.bootstrap import run_historical_bootstrap


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

        # 8. All recorded processing states have last_generated_at == as_of
        assert len(recorded_successes) == 6
        target_types = {item[2] for item in recorded_successes}
        assert target_types == {"journey", "profile", "segment", "merchant_health"}
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

