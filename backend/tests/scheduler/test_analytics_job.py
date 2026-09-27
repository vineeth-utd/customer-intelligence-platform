import pytest
import datetime
from unittest.mock import patch, AsyncMock
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.scheduler.analytics_job import run_analytics_job
from app.scheduler.main import setup_scheduler, stop_scheduler, scheduler
from app.config.settings import settings


@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setattr(settings, "analytics_job_lookback_days", 1)
    monkeypatch.setattr(settings, "enable_background_scheduler", True)
    return settings


@pytest.mark.asyncio
@patch("app.scheduler.analytics_job.refresh_aggregate_views")
@patch("app.scheduler.analytics_job.generate_daily_metrics")
@patch("app.scheduler.analytics_job.AsyncSessionLocal")
async def test_run_analytics_job_success(
    mock_session_maker, mock_generate, mock_refresh, mock_settings
):
    # Setup mock session
    mock_session = AsyncMock()
    # async context manager protocol
    mock_session_maker.return_value.__aenter__.return_value = mock_session
    mock_session_maker.return_value.__aexit__.return_value = None

    # Run the job
    await run_analytics_job()

    # Verify calls
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    expected_dates = [
        now_utc.date(),
        (now_utc - datetime.timedelta(days=1)).date()
    ]
    
    # generation called once per selected date
    assert mock_generate.call_count == 2
    calls = mock_generate.call_args_list
    actual_dates = [call[0][1] for call in calls]
    assert actual_dates == expected_dates
    
    # commit each date independently
    assert mock_session.commit.call_count == 2
    
    # materialized views refreshed exactly once after successful generation
    assert mock_refresh.call_count == 1
    assert mock_refresh.call_args[0][0] == mock_session


@pytest.mark.asyncio
@patch("app.scheduler.analytics_job.refresh_aggregate_views")
@patch("app.scheduler.analytics_job.generate_daily_metrics")
@patch("app.scheduler.analytics_job.AsyncSessionLocal")
async def test_run_analytics_job_failure(
    mock_session_maker, mock_generate, mock_refresh, mock_settings
):
    mock_session = AsyncMock()
    mock_session_maker.return_value.__aenter__.return_value = mock_session
    mock_session_maker.return_value.__aexit__.return_value = None

    # Simulate a failure on the first generation call
    mock_generate.side_effect = Exception("Database error")

    with pytest.raises(Exception, match="Database error"):
        await run_analytics_job()

    # Generation failed on the first call, so it shouldn't proceed
    assert mock_generate.call_count == 1
    
    # Materialized view refresh must NOT be called if generation fails
    mock_refresh.assert_not_called()


@patch("app.scheduler.main.scheduler.start")
def test_scheduler_registration(mock_start, mock_settings, monkeypatch):
    # Ensure it's empty to start
    scheduler.remove_all_jobs()
    
    setup_scheduler()
    
    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    job = jobs[0]
    
    assert job.id == "analytics_job"
    assert job.max_instances == 1
    assert job.coalesce is True
    assert isinstance(job.trigger, CronTrigger)
    
    mock_start.assert_called_once()
    
    # We do not call stop_scheduler() because it was mocked to start
    # but we can remove the job for cleanup
    scheduler.remove_all_jobs()
