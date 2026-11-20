import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.order import (
    get_order as dal_get_order,
    list_merchant_orders_paginated,
    list_shopper_orders_paginated,
)
from app.models.order import Order


async def get_order(session: AsyncSession, order_id: uuid.UUID) -> Order | None:
    return await dal_get_order(session, order_id)


async def list_orders(session: AsyncSession, merchant_id: uuid.UUID, limit: int, offset: int) -> tuple[list[Order], int]:
    return await list_merchant_orders_paginated(session, merchant_id, limit, offset)


async def list_shopper_orders(
    session: AsyncSession, merchant_id: uuid.UUID, shopper_id: uuid.UUID, limit: int, offset: int
) -> tuple[list[Order], int]:
    return await list_shopper_orders_paginated(session, merchant_id, shopper_id, limit, offset)
