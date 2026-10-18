import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.segment import (
    count_segment_members as dal_count_segment_members,
    get_merchant_segments,
    get_merchant_shopper_ids,
    get_segment_by_id,
    get_segment_members_paginated as dal_get_segment_members_paginated,
    get_shopper_merchant_id,
    get_shopper_segment_memberships as dal_get_shopper_segment_memberships,
    sync_segment_memberships_for_segment,
    sync_shopper_segment_memberships,
    upsert_merchant_segment,
)
from app.models.segmentation import ShopperSegmentMember
from app.models.shopper import ShopperSegment
from app.reference_data.segments import SEGMENT_CATALOG
from app.services.segment_rules import evaluate_segment_rule


async def initialize_merchant_segments(session: AsyncSession, merchant_id: uuid.UUID) -> None:
    """Initialize canonical V1 segments for the given merchant.
    
    Persists or updates the catalog definitions. Caller is responsible for
    providing a session and committing the transaction.
    """
    for entry in SEGMENT_CATALOG:
        await upsert_merchant_segment(session, merchant_id, entry)


async def refresh_shopper_segment_membership_callback(
    session: AsyncSession, shopper_id: uuid.UUID
) -> None:
    """
    Incremental processor callback for refreshing segment memberships for a single shopper.
    Evaluates all active segments for the shopper's merchant and atomically synchronizes
    the shopper's membership records.
    """
    merchant_id = await get_shopper_merchant_id(session, shopper_id)
    if not merchant_id:
        return

    segments = await get_merchant_segments(session, merchant_id)
    if not segments:
        await sync_shopper_segment_memberships(session, shopper_id, set(), datetime.now(timezone.utc))
        return

    now = datetime.now(timezone.utc)
    matching_segment_ids: set[uuid.UUID] = set()

    for seg in segments:
        matches = await evaluate_segment_rule(
            session=session,
            shopper_id=shopper_id,
            definition=seg.segment_definition,
            evaluation_time=now,
        )
        if matches:
            matching_segment_ids.add(seg.segment_id)

    await sync_shopper_segment_memberships(session, shopper_id, matching_segment_ids, now)


async def refresh_segment_memberships_for_segment(
    session: AsyncSession, segment_id: uuid.UUID
) -> None:
    """
    Reevaluates and synchronizes memberships for all shoppers under a given segment's merchant.
    Used when a segment definition is updated or created.
    """
    segment = await get_segment_by_id(session, segment_id)
    if not segment:
        return

    shopper_ids = await get_merchant_shopper_ids(session, segment.merchant_id)
    now = datetime.now(timezone.utc)
    matching_shopper_ids: set[uuid.UUID] = set()

    for shp_id in shopper_ids:
        matches = await evaluate_segment_rule(
            session=session,
            shopper_id=shp_id,
            definition=segment.segment_definition,
            evaluation_time=now,
        )
        if matches:
            matching_shopper_ids.add(shp_id)

    await sync_segment_memberships_for_segment(session, segment_id, matching_shopper_ids, now)


async def refresh_all_segments_for_merchant(
    session: AsyncSession, merchant_id: uuid.UUID
) -> None:
    """
    Refresh all segment memberships for all shoppers of a merchant.
    """
    shopper_ids = await get_merchant_shopper_ids(session, merchant_id)
    for shp_id in shopper_ids:
        await refresh_shopper_segment_membership_callback(session, shp_id)


async def update_segment_definition(
    session: AsyncSession, segment_id: uuid.UUID, new_definition: dict
) -> ShopperSegment:
    """
    Updates a segment definition and immediately triggers reevaluation of the
    affected merchant's shoppers, maintaining deterministic membership state.
    """
    segment = await get_segment_by_id(session, segment_id)
    if not segment:
        raise ValueError(f"Segment {segment_id} not found")

    segment.segment_definition = new_definition
    await session.flush()

    await refresh_segment_memberships_for_segment(session, segment_id)
    return segment


async def get_segments_for_shopper(
    session: AsyncSession, shopper_id: uuid.UUID
) -> Sequence[ShopperSegmentMember]:
    """Retrieve all segment memberships for a shopper."""
    return await dal_get_shopper_segment_memberships(session, shopper_id)


async def get_members_for_segment(
    session: AsyncSession, segment_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> tuple[Sequence[ShopperSegmentMember], int]:
    """Retrieve paginated members belonging to a segment with total count."""
    return await dal_get_segment_members_paginated(session, segment_id, limit=limit, offset=offset)


async def get_segment_member_count(session: AsyncSession, segment_id: uuid.UUID) -> int:
    """Count members belonging to a segment."""
    return await dal_count_segment_members(session, segment_id)
