import uuid
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, ProductVariant


async def get_product_by_id(session: AsyncSession, product_id: uuid.UUID) -> Product | None:
    stmt = select(Product).where(Product.product_id == product_id).execution_options(populate_existing=True)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_product(
    session: AsyncSession,
    *,
    product_id: uuid.UUID,
    merchant_id: uuid.UUID,
    product_name: str,
    category: str | None,
    vendor: str | None,
    status: str,
) -> None:
    """Insert a products row for this product_id if one doesn't exist yet.

    Idempotent (ON CONFLICT DO NOTHING on the product_id primary key) since
    PRODUCT_CREATED may be redelivered. Does not commit.
    """
    stmt = (
        pg_insert(Product)
        .values(
            product_id=product_id,
            merchant_id=merchant_id,
            product_name=product_name,
            category=category,
            vendor=vendor,
            status=status,
        )
        .on_conflict_do_nothing(index_elements=["product_id"])
    )
    await session.execute(stmt)


async def update_product_fields(session: AsyncSession, product_id: uuid.UUID, fields: dict[str, object]) -> None:
    if not fields:
        return
    stmt = update(Product).where(Product.product_id == product_id).values(**fields)
    await session.execute(stmt)


async def archive_product(session: AsyncSession, product_id: uuid.UUID) -> None:
    stmt = update(Product).where(Product.product_id == product_id).values(status="archived")
    await session.execute(stmt)


async def archive_product_variants(session: AsyncSession, product_id: uuid.UUID) -> None:
    """Archive every non-archived variant under this product.

    Deterministic bulk effect of PRODUCT_ARCHIVED. Safe to re-run: variants
    already archived are excluded by the WHERE clause, so redelivery is a no-op.
    """
    stmt = (
        update(ProductVariant)
        .where(ProductVariant.product_id == product_id, ProductVariant.status != "archived")
        .values(status="archived")
    )
    await session.execute(stmt)


async def get_product_variant_by_id(session: AsyncSession, variant_id: uuid.UUID) -> ProductVariant | None:
    stmt = (
        select(ProductVariant).where(ProductVariant.variant_id == variant_id).execution_options(populate_existing=True)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_product_variant(
    session: AsyncSession,
    *,
    variant_id: uuid.UUID,
    product_id: uuid.UUID,
    variant_name: str,
    sku: str,
    price: Decimal,
    size: str | None,
    color: str | None,
    inventory_quantity: int,
    status: str,
) -> None:
    """Insert a product_variants row for this variant_id if one doesn't exist yet.

    Idempotent (ON CONFLICT DO NOTHING on the variant_id primary key) since
    PRODUCT_VARIANT_CREATED may be redelivered. product_id carries an
    enforced foreign key to products, so this fails loudly if the parent
    Product row does not exist yet - correct in-order delivery of
    PRODUCT_CREATED before its variant events (both share the same Kafka
    partition key) prevents that. Does not commit.
    """
    stmt = (
        pg_insert(ProductVariant)
        .values(
            variant_id=variant_id,
            product_id=product_id,
            variant_name=variant_name,
            sku=sku,
            price=price,
            size=size,
            color=color,
            inventory_quantity=inventory_quantity,
            status=status,
        )
        .on_conflict_do_nothing(index_elements=["variant_id"])
    )
    await session.execute(stmt)


def apply_variant_field_changes(variant: ProductVariant, changed_values: dict[str, object]) -> None:
    for field_name, value in changed_values.items():
        setattr(variant, field_name, value)


def archive_variant_row(variant: ProductVariant) -> None:
    variant.status = "archived"
