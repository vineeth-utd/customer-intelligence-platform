import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.segmentation import ShopperSegmentMember
from app.models.shopper import Shopper, ShopperSegment
from app.reference_data.segments import SegmentCatalogEntry


async def get_segment_by_id(session: AsyncSession, segment_id: uuid.UUID) -> ShopperSegment | None:
    """Retrieve a single ShopperSegment by segment_id."""
    result = await session.execute(
        select(ShopperSegment).where(ShopperSegment.segment_id == segment_id)
    )
    return result.scalars().first()


async def get_merchant_segments(session: AsyncSession, merchant_id: uuid.UUID) -> Sequence[ShopperSegment]:
    """Retrieve all initialized segments for a given merchant."""
    result = await session.execute(
        select(ShopperSegment)
        .where(ShopperSegment.merchant_id == merchant_id)
        .order_by(ShopperSegment.segment_name)
    )
    return result.scalars().all()


async def upsert_merchant_segment(
    session: AsyncSession, merchant_id: uuid.UUID, entry: SegmentCatalogEntry
) -> ShopperSegment:
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


async def get_shopper_merchant_id(session: AsyncSession, shopper_id: uuid.UUID) -> uuid.UUID | None:
    """Retrieve the merchant_id associated with a shopper."""
    stmt = select(Shopper.merchant_id).where(Shopper.shopper_id == shopper_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_merchant_shopper_ids(session: AsyncSession, merchant_id: uuid.UUID) -> Sequence[uuid.UUID]:
    """Retrieve all shopper IDs for a given merchant."""
    stmt = select(Shopper.shopper_id).where(Shopper.merchant_id == merchant_id)
    result = await session.execute(stmt)
    return result.scalars().all()


async def sync_shopper_segment_memberships(
    session: AsyncSession,
    shopper_id: uuid.UUID,
    matching_segment_ids: set[uuid.UUID] | list[uuid.UUID],
    generated_at: datetime,
) -> None:
    """
    Synchronize the segment memberships of a single shopper atomically and idempotently.
    Prunes revoked memberships and upserts qualifying memberships.
    """
    matching_set = set(matching_segment_ids)

    # 1. Prune memberships that no longer qualify
    if matching_set:
        delete_stmt = delete(ShopperSegmentMember).where(
            ShopperSegmentMember.shopper_id == shopper_id,
            ShopperSegmentMember.segment_id.not_in(matching_set),
        )
    else:
        delete_stmt = delete(ShopperSegmentMember).where(
            ShopperSegmentMember.shopper_id == shopper_id
        )
    await session.execute(delete_stmt)

    # 2. Upsert currently qualifying memberships
    if matching_set:
        for seg_id in matching_set:
            insert_stmt = (
                pg_insert(ShopperSegmentMember)
                .values(
                    segment_id=seg_id,
                    shopper_id=shopper_id,
                    generated_at=generated_at,
                )
                .on_conflict_do_update(
                    index_elements=["segment_id", "shopper_id"],
                    set_={"generated_at": generated_at},
                )
            )
            await session.execute(insert_stmt)


async def sync_segment_memberships_for_segment(
    session: AsyncSession,
    segment_id: uuid.UUID,
    matching_shopper_ids: set[uuid.UUID] | list[uuid.UUID],
    generated_at: datetime,
) -> None:
    """
    Synchronize all memberships for a single segment atomically and idempotently.
    Prunes revoked memberships and upserts qualifying memberships.
    """
    matching_set = set(matching_shopper_ids)

    # 1. Prune memberships that no longer qualify
    if matching_set:
        delete_stmt = delete(ShopperSegmentMember).where(
            ShopperSegmentMember.segment_id == segment_id,
            ShopperSegmentMember.shopper_id.not_in(matching_set),
        )
    else:
        delete_stmt = delete(ShopperSegmentMember).where(
            ShopperSegmentMember.segment_id == segment_id
        )
    await session.execute(delete_stmt)

    # 2. Upsert currently qualifying memberships
    if matching_set:
        for shp_id in matching_set:
            insert_stmt = (
                pg_insert(ShopperSegmentMember)
                .values(
                    segment_id=segment_id,
                    shopper_id=shp_id,
                    generated_at=generated_at,
                )
                .on_conflict_do_update(
                    index_elements=["segment_id", "shopper_id"],
                    set_={"generated_at": generated_at},
                )
            )
            await session.execute(insert_stmt)


async def get_shopper_segment_memberships(
    session: AsyncSession, shopper_id: uuid.UUID
) -> Sequence[ShopperSegmentMember]:
    """Retrieve all segment memberships for a shopper, eager-loading segment definition metadata."""
    stmt = (
        select(ShopperSegmentMember)
        .options(selectinload(ShopperSegmentMember.segment))
        .where(ShopperSegmentMember.shopper_id == shopper_id)
        .order_by(ShopperSegmentMember.generated_at.desc(), ShopperSegmentMember.segment_id.asc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_segment_members_paginated(
    session: AsyncSession, segment_id: uuid.UUID, limit: int = 50, offset: int = 0
) -> tuple[Sequence[ShopperSegmentMember], int]:
    """Retrieve members for a given segment with deterministic ordering, eager-loading shopper details, and total count."""
    count_stmt = select(func.count()).select_from(ShopperSegmentMember).where(
        ShopperSegmentMember.segment_id == segment_id
    )
    total_count = (await session.execute(count_stmt)).scalar() or 0

    stmt = (
        select(ShopperSegmentMember)
        .options(selectinload(ShopperSegmentMember.shopper))
        .where(ShopperSegmentMember.segment_id == segment_id)
        .order_by(ShopperSegmentMember.generated_at.desc(), ShopperSegmentMember.shopper_id.asc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    members = result.scalars().all()

    return members, total_count


async def count_segment_members(session: AsyncSession, segment_id: uuid.UUID) -> int:
    """Count current members in a segment."""
    stmt = select(func.count()).select_from(ShopperSegmentMember).where(
        ShopperSegmentMember.segment_id == segment_id
    )
    return (await session.execute(stmt)).scalar() or 0
