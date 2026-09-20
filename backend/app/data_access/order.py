import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.order import Order, OrderItem


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

async def list_merchant_orders(session: AsyncSession, merchant_id: uuid.UUID) -> list[Order]:
    """Retrieve all orders for a given merchant."""
    stmt = select(Order).where(Order.merchant_id == merchant_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())
