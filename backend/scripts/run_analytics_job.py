import asyncio
import logging
from app.scheduler.analytics_job import run_analytics_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("Manually triggering analytics job execution.")
    try:
        await run_analytics_job()
        logger.info("Manual analytics job execution completed successfully.")
    except Exception as e:
        logger.error("Manual analytics job execution failed.", exc_info=e)

if __name__ == "__main__":
    asyncio.run(main())
