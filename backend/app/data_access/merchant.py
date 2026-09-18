from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.merchant import PlatformFeature, SubscriptionPlan
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
