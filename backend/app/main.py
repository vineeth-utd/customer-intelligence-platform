import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.kafka.producer import event_producer
from app.scheduler.main import setup_scheduler, stop_scheduler
from app.api import analytics, merchants

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    try:
        await event_producer.start()
    except Exception:
        logger.warning("Kafka producer failed to start; continuing without Kafka publishing", exc_info=True)
        
    try:
        setup_scheduler()
    except Exception:
        logger.error("Background scheduler failed to start", exc_info=True)
        
    yield
    
    stop_scheduler()
    await event_producer.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_allowed_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analytics.router)
app.include_router(merchants.router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "environment": settings.environment}
