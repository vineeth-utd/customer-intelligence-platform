import uuid
from datetime import datetime

from sqlalchemy import func, select, update, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shopper import Shopper


async def upsert_shopper(
    session: AsyncSession, merchant_id: uuid.UUID, shopper_id: uuid.UUID, event_timestamp: datetime
) -> Shopper:
    stmt = (
        pg_insert(Shopper)
        .values(
            shopper_id=shopper_id,
            merchant_id=merchant_id,
            first_seen_at=event_timestamp,
            last_seen_at=event_timestamp,
        )
        .on_conflict_do_update(
            index_elements=["shopper_id"],
            set_={
                "last_seen_at": func.greatest(Shopper.last_seen_at, event_timestamp),
            },
        )
        .returning(Shopper)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def enrich_shopper_email(
    session: AsyncSession, merchant_id: uuid.UUID, shopper_id: uuid.UUID, email: str
) -> bool:
    """Attempt to enrich shopper with email. Returns False if conflict."""
    # Check if email is already used by another shopper under the same merchant
    stmt = select(Shopper.shopper_id).where(
        and_(Shopper.merchant_id == merchant_id, Shopper.email == email, Shopper.shopper_id != shopper_id)
    )
    existing_other = await session.scalar(stmt)
    if existing_other is not None:
        return False

    update_stmt = (
        update(Shopper)
        .where(Shopper.shopper_id == shopper_id, Shopper.email.is_(None))
        .values(email=email)
    )
    await session.execute(update_stmt)
    return True

async def list_merchant_shoppers(session: AsyncSession, merchant_id: uuid.UUID) -> list[uuid.UUID]:
    """Retrieve all shopper IDs for a given merchant."""
    stmt = select(Shopper.shopper_id).where(Shopper.merchant_id == merchant_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def list_merchant_shoppers_paginated(session: AsyncSession, merchant_id: uuid.UUID, limit: int, offset: int) -> tuple[list[Shopper], int]:
    """Retrieve shoppers for a merchant with pagination."""
    count_stmt = select(func.count(Shopper.shopper_id)).where(Shopper.merchant_id == merchant_id)
    total = await session.scalar(count_stmt)
    
    stmt = select(Shopper).where(Shopper.merchant_id == merchant_id).order_by(Shopper.shopper_id).limit(limit).offset(offset)
    result = await session.execute(stmt)
    items = list(result.scalars().all())
    return items, total or 0
