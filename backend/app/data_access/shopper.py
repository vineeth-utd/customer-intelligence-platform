import uuid
from datetime import datetime

from sqlalchemy import select, update, and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shopper import Shopper
from app.models.order import Order, OrderItem
from app.models.product import Product, ProductVariant
from app.models.merchant import Merchant


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
            set_={"last_seen_at": event_timestamp},
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


async def get_merchant(session: AsyncSession, merchant_id: uuid.UUID) -> Merchant | None:
    return await session.get(Merchant, merchant_id)


async def get_order(session: AsyncSession, order_id: uuid.UUID) -> Order | None:
    return await session.get(Order, order_id)


async def create_order(
    session: AsyncSession,
    order_id: uuid.UUID,
    merchant_id: uuid.UUID,
    shopper_id: uuid.UUID,
    currency: str,
    total_amount: float,
    placed_at: datetime,
    completed_at: datetime | None = None,
) -> Order:
    order = Order(
        order_id=order_id,
        merchant_id=merchant_id,
        shopper_id=shopper_id,
        order_status="completed",
        currency=currency,
        total_amount=total_amount,
        placed_at=placed_at,
        completed_at=completed_at,
    )
    session.add(order)
    return order


async def get_product_variant_with_product(session: AsyncSession, variant_id: uuid.UUID) -> tuple[ProductVariant, Product] | None:
    stmt = (
        select(ProductVariant, Product)
        .join(Product, ProductVariant.product_id == Product.product_id)
        .where(ProductVariant.variant_id == variant_id)
        .with_for_update()  # Lock for inventory update
    )
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        return None
    return row[0], row[1]


async def decrement_inventory(session: AsyncSession, variant_id: uuid.UUID, quantity: int) -> bool:
    stmt = (
        update(ProductVariant)
        .where(ProductVariant.variant_id == variant_id, ProductVariant.inventory_quantity >= quantity)
        .values(inventory_quantity=ProductVariant.inventory_quantity - quantity)
    )
    result = await session.execute(stmt)
    return result.rowcount > 0


def create_order_items(
    session: AsyncSession,
    order_id: uuid.UUID,
    items_data: list[tuple[uuid.UUID, int, float, float]] # (variant_id, quantity, unit_price, line_total)
) -> None:
    for variant_id, quantity, unit_price, line_total in items_data:
        item = OrderItem(
            order_id=order_id,
            variant_id=variant_id,
            quantity=quantity,
            unit_price=unit_price,
            line_total=line_total,
        )
        session.add(item)
