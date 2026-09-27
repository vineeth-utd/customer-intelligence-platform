import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shopper import ShopperSegment
from app.reference_data.segments import SegmentCatalogEntry


async def get_merchant_segments(session: AsyncSession, merchant_id: uuid.UUID) -> Sequence[ShopperSegment]:
    """Retrieve all initialized segments for a given merchant."""
    result = await session.execute(
        select(ShopperSegment)
        .where(ShopperSegment.merchant_id == merchant_id)
        .order_by(ShopperSegment.segment_name)
    )
    return result.scalars().all()


async def upsert_merchant_segment(session: AsyncSession, merchant_id: uuid.UUID, entry: SegmentCatalogEntry) -> ShopperSegment:
    """Insert or update a ShopperSegment by merchant_id and segment_name.
    
    Since there is no database-level unique constraint on (merchant_id, segment_name),
    we perform a SELECT and then UPDATE/INSERT.
    """
    result = await session.execute(
        select(ShopperSegment)
        .where(
            ShopperSegment.merchant_id == merchant_id,
            ShopperSegment.segment_name == entry.segment_name,
        )
    )
    segment = result.scalars().first()

    if segment:
        segment.segment_definition = entry.segment_definition
    else:
        segment = ShopperSegment(
            merchant_id=merchant_id,
            segment_name=entry.segment_name,
            segment_definition=entry.segment_definition,
        )
        session.add(segment)
        
    return segment

