from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.merchant import get_feature_by_key, get_plan_by_key, upsert_feature, upsert_plan
from app.models.merchant import PlatformFeature, SubscriptionPlan
from app.reference_data.features import FEATURE_CATALOG, FeatureKey
from app.reference_data.plans import PLAN_CATALOG, PlanKey


async def resolve_plan(session: AsyncSession, plan_key: PlanKey) -> SubscriptionPlan | None:
    return await get_plan_by_key(session, plan_key)


async def resolve_feature(session: AsyncSession, feature_key: FeatureKey) -> PlatformFeature | None:
    return await get_feature_by_key(session, feature_key)


async def initialize_reference_data(session: AsyncSession) -> None:
    """Seed subscription_plans and platform_features from the canonical code catalogs.

    Idempotent (upsert by natural key) and safe to re-run. Owns the
    transaction for the whole initialization as one unit; the Data Access
    functions it calls operate on the session without committing.
    """
    for entry in PLAN_CATALOG.values():
        await upsert_plan(session, entry)
    for entry in FEATURE_CATALOG.values():
        await upsert_feature(session, entry)
    await session.commit()
