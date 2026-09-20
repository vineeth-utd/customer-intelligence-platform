"""Standalone entrypoint to initialize default ShopperSegments for existing merchants.

Usage (from backend/):
    uv run python -m scripts.init_segments
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.merchant import Merchant
from app.services.segment import initialize_merchant_segments

logger = logging.getLogger(__name__)


async def _run() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Merchant.merchant_id))
        merchant_ids = result.scalars().all()
        
        for mid in merchant_ids:
            await initialize_merchant_segments(session, mid)
            
        await session.commit()
        logger.info(f"Initialized segments for {len(merchant_ids)} merchants.")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_run())


if __name__ == "__main__":
    main()
