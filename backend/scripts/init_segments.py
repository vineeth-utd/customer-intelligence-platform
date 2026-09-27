"""Standalone entrypoint to initialize default ShopperSegments for existing merchants.

Usage (from backend/):
    uv run python -m scripts.init_segments
"""

import asyncio
import logging

from app.db.session import AsyncSessionLocal
from app.data_access.merchant import list_installed_merchants
from app.services.segment import initialize_merchant_segments

logger = logging.getLogger(__name__)


async def _run() -> None:
    async with AsyncSessionLocal() as session:
        merchants = await list_installed_merchants(session)
        
        for m in merchants:
            await initialize_merchant_segments(session, m.merchant_id)
            
        await session.commit()
        logger.info(f"Initialized segments for {len(merchants)} merchants.")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_run())


if __name__ == "__main__":
    main()
