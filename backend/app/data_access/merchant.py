import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.merchant import Merchant, MerchantFeature, PlatformFeature, Subscription, SubscriptionPlan
from app.reference_data.features import FeatureCatalogEntry, FeatureKey
from app.reference_data.plans import PlanCatalogEntry, PlanKey


async def get_plan_by_key(session: AsyncSession, plan_key: PlanKey) -> SubscriptionPlan | None:
    # populate_existing refreshes an already-loaded ORM instance from this
    # row, since upsert_plan writes through Core and would otherwise leave a
    # stale object in the session's identity map.
    stmt = (
        select(SubscriptionPlan)
        .where(SubscriptionPlan.plan_key == plan_key.value)
        .execution_options(populate_existing=True)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_feature_by_key(session: AsyncSession, feature_key: FeatureKey) -> PlatformFeature | None:
    stmt = (
        select(PlatformFeature)
        .where(PlatformFeature.feature_key == feature_key.value)
        .execution_options(populate_existing=True)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_plan(session: AsyncSession, entry: PlanCatalogEntry) -> None:
    """Insert or refresh a subscription_plans row keyed by plan_key.

    Operates on the provided session without committing - transaction
    ownership stays with the caller.
    """
    stmt = (
        pg_insert(SubscriptionPlan)
        .values(
            plan_key=entry.plan_key.value,
            plan_name=entry.plan_name,
            monthly_price=entry.monthly_price,
            annual_price=entry.annual_price,
        )
        .on_conflict_do_update(
            index_elements=["plan_key"],
            set_={
                "plan_name": entry.plan_name,
                "monthly_price": entry.monthly_price,
                "annual_price": entry.annual_price,
            },
        )
    )
    await session.execute(stmt)


async def upsert_feature(session: AsyncSession, entry: FeatureCatalogEntry) -> None:
    """Insert or refresh a platform_features row keyed by feature_key.

    Operates on the provided session without committing - transaction
    ownership stays with the caller.
    """
    stmt = (
        pg_insert(PlatformFeature)
        .values(
            feature_key=entry.feature_key.value,
            feature_name=entry.feature_name,
            feature_category=entry.feature_category,
        )
        .on_conflict_do_update(
            index_elements=["feature_key"],
            set_={
                "feature_name": entry.feature_name,
                "feature_category": entry.feature_category,
            },
        )
    )
    await session.execute(stmt)


async def get_merchant_by_id(session: AsyncSession, merchant_id: uuid.UUID) -> Merchant | None:
    stmt = select(Merchant).where(Merchant.merchant_id == merchant_id).execution_options(populate_existing=True)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_merchant(
    session: AsyncSession,
    *,
    merchant_id: uuid.UUID,
    shopify_store_id: str,
    merchant_name: str,
    email: str,
    country: str,
    timezone: str,
    store_currency: str,
    app_install_status: str,
) -> None:
    """Insert a merchants row for this merchant_id if one doesn't exist yet.

    Idempotent (ON CONFLICT DO NOTHING on the merchant_id primary key) since
    MERCHANT_CREATED may be redelivered. Does not commit.
    """
    stmt = (
        pg_insert(Merchant)
        .values(
            merchant_id=merchant_id,
            shopify_store_id=shopify_store_id,
            merchant_name=merchant_name,
            email=email,
            country=country,
            timezone=timezone,
            store_currency=store_currency,
            app_install_status=app_install_status,
        )
        .on_conflict_do_nothing(index_elements=["merchant_id"])
    )
    await session.execute(stmt)


async def update_merchant_install_status(
    session: AsyncSession, merchant_id: uuid.UUID, app_install_status: str, updated_at: datetime
) -> None:
    stmt = (
        update(Merchant)
        .where(Merchant.merchant_id == merchant_id)
        .values(app_install_status=app_install_status, last_install_status_updated_at=updated_at)
    )
    await session.execute(stmt)


async def update_merchant_last_active_at(session: AsyncSession, merchant_id: uuid.UUID, last_active_at: datetime) -> None:
    stmt = update(Merchant).where(Merchant.merchant_id == merchant_id).values(last_active_at=last_active_at)
    await session.execute(stmt)


async def update_merchant_fields(session: AsyncSession, merchant_id: uuid.UUID, fields: dict[str, object]) -> None:
    if not fields:
        return
    stmt = update(Merchant).where(Merchant.merchant_id == merchant_id).values(**fields)
    await session.execute(stmt)


async def get_active_subscription(session: AsyncSession, merchant_id: uuid.UUID) -> Subscription | None:
    stmt = (
        select(Subscription)
        .where(Subscription.merchant_id == merchant_id, Subscription.status == "active")
        .execution_options(populate_existing=True)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_active_subscription(
    session: AsyncSession,
    *,
    merchant_id: uuid.UUID,
    plan_id: uuid.UUID,
    billing_cycle: str,
    amount_paid: float,
    started_at: datetime,
) -> None:
    """Ensure the merchant has exactly one active subscription with these attributes.

    Updates the existing active subscription in place if one exists,
    otherwise creates one - this keeps SUBSCRIPTION_STARTED replay-safe
    (redelivery does not create a second active subscription for the same
    merchant). Does not commit; flushes so the row is visible to subsequent
    queries within the same transaction.
    """
    subscription = await get_active_subscription(session, merchant_id)
    if subscription is not None:
        subscription.plan_id = plan_id
        subscription.billing_cycle = billing_cycle
        subscription.amount_paid = amount_paid
        subscription.started_at = started_at
        return
    session.add(
        Subscription(
            merchant_id=merchant_id,
            plan_id=plan_id,
            status="active",
            billing_cycle=billing_cycle,
            amount_paid=amount_paid,
            started_at=started_at,
        )
    )
    await session.flush()


def update_subscription_renewal(
    subscription: Subscription, *, renewal_at: datetime, amount_paid: float, billing_cycle: str
) -> None:
    subscription.renewal_at = renewal_at
    subscription.amount_paid = amount_paid
    subscription.billing_cycle = billing_cycle


def update_subscription_plan(subscription: Subscription, *, plan_id: uuid.UUID, billing_cycle: str, amount_paid: float) -> None:
    subscription.plan_id = plan_id
    subscription.billing_cycle = billing_cycle
    subscription.amount_paid = amount_paid


def cancel_subscription(subscription: Subscription, *, cancelled_at: datetime) -> None:
    subscription.status = "cancelled"
    subscription.cancelled_at = cancelled_at


async def upsert_merchant_feature(
    session: AsyncSession, *, merchant_id: uuid.UUID, feature_id: uuid.UUID, is_enabled: bool
) -> None:
    stmt = (
        pg_insert(MerchantFeature)
        .values(merchant_id=merchant_id, feature_id=feature_id, is_enabled=is_enabled)
        .on_conflict_do_update(
            index_elements=["merchant_id", "feature_id"],
            set_={"is_enabled": is_enabled},
        )
    )
    await session.execute(stmt)
