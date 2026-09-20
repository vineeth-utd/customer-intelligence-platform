import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.segment import upsert_merchant_segment, get_merchant_segments
from app.reference_data.segments import SEGMENT_CATALOG


async def initialize_merchant_segments(session: AsyncSession, merchant_id: uuid.UUID) -> None:
    """Initialize canonical V1 segments for the given merchant.
    
    Persists or updates the catalog definitions. Caller is responsible for
    providing a session and committing the transaction.
    """
    for entry in SEGMENT_CATALOG:
        await upsert_merchant_segment(session, merchant_id, entry)

