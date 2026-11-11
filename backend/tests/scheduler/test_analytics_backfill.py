"""Unit tests for analytics range backfill and CLI arguments."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.scheduler.analytics_job import run_analytics_job


@pytest.mark.asyncio
async def test_analytics_job_rejects_inverted_dates():
    with pytest.raises(ValueError, match="start_date .* must not be greater than end_date"):
        await run_analytics_job(
            start_date=date(2026, 10, 15),
            end_date=date(2026, 10, 10),
        )


@pytest.mark.asyncio
async def test_analytics_job_rejects_single_date():
    with pytest.raises(ValueError, match="Both start_date and end_date must be provided"):
        await run_analytics_job(start_date=date(2026, 10, 10), end_date=None)

    with pytest.raises(ValueError, match="Both start_date and end_date must be provided"):
        await run_analytics_job(start_date=None, end_date=date(2026, 10, 10))


@pytest.mark.asyncio
async def test_analytics_job_computes_ascending_date_sequence():
    start = date(2026, 9, 1)
    end = date(2026, 9, 5)

    computed_dates = []

    async def mock_generate(session, metric_date):
        computed_dates.append(metric_date)

    with (
        patch("app.scheduler.analytics_job.generate_daily_metrics", side_effect=mock_generate),
        patch("app.scheduler.analytics_job.refresh_aggregate_views", new_callable=AsyncMock) as mock_refresh,
        patch("app.scheduler.analytics_job.AsyncSessionLocal") as mock_session_local,
    ):
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        await run_analytics_job(start_date=start, end_date=end)

        assert computed_dates == [
            date(2026, 9, 1),
            date(2026, 9, 2),
            date(2026, 9, 3),
            date(2026, 9, 4),
            date(2026, 9, 5),
        ]
        assert mock_refresh.called
        assert mock_session.commit.call_count == 5

