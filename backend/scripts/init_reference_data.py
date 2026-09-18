"""Standalone entrypoint to initialize canonical merchant reference data.

Upserts the subscription-plan and platform-feature catalogs defined in
app/reference_data/ into subscription_plans/platform_features by their
natural key (plan_key/feature_key). Idempotent - safe to re-run whenever the
catalogs change.

Usage (from backend/):
    uv run python -m scripts.init_reference_data
"""

import asyncio
import logging

from app.db.session import AsyncSessionLocal
from app.services.merchant import initialize_reference_data

logger = logging.getLogger(__name__)


async def _run() -> None:
    async with AsyncSessionLocal() as session:
        await initialize_reference_data(session)
    logger.info("Reference data initialized")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_run())


if __name__ == "__main__":
    main()
