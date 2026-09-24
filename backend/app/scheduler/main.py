import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config.settings import settings
from app.scheduler.analytics_job import run_analytics_job

logger = logging.getLogger(__name__)

# Single scheduler instance embedded in the FastAPI application.
# NOTE: This is a Phase 1 single-backend-instance design. 
# Multi-replica deployment would require a distributed job store (e.g. SQLAlchemyJobStore)
# or dedicated background worker instances.
scheduler = AsyncIOScheduler()

def setup_scheduler():
    """
    Configures and starts the background scheduler.
    Registers the analytics job according to the configured cadence.
    """
    if not settings.enable_background_scheduler:
        logger.info("Background scheduler is disabled by settings.")
        return

    # Add the analytics job
    # max_instances=1 and coalesce=True prevent overlapping execution of the same job
    scheduler.add_job(
        run_analytics_job,
        trigger=CronTrigger(minute=settings.analytics_job_cron_minute),
        id="analytics_job",
        name="Generate daily analytics and refresh views",
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    
    logger.info(f"Registered analytics job to run at minute {settings.analytics_job_cron_minute} of every hour.")
    
    scheduler.start()
    logger.info("Background scheduler started.")

def stop_scheduler():
    """
    Gracefully shuts down the background scheduler.
    """
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped.")
