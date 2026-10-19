import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_access.processing_state import record_domain_activity
from app.data_access.profile import (
    get_merchant_profile as dal_get_merchant_profile,
    get_merchant_profile_source_data,
    get_shopper_profile as dal_get_shopper_profile,
    get_shopper_profile_source_data,
    upsert_merchant_profile,
    upsert_shopper_profile,
)
from app.models.profile import MerchantProfile, ShopperProfile


async def generate_merchant_profile_callback(session: AsyncSession, merchant_id: uuid.UUID) -> None:
    """
    Incremental processor callback for regenerating a Merchant Profile.
    Calculates derived metrics and upserts the profile.
    """
    # 1. Fetch raw operational aggregates
    data = await get_merchant_profile_source_data(session, merchant_id)
    
    # 2. Calculate dependent derived fields
    total_orders = data["total_orders"]
    total_revenue = data["total_revenue"]
    
    if total_orders > 0:
        data["average_order_value"] = total_revenue / total_orders
    else:
        data["average_order_value"] = 0.0

    total_sessions = data["total_sessions"]
    converted_sessions = data["converted_sessions"]
    
    if total_sessions > 0:
        data["conversion_rate"] = converted_sessions / total_sessions
    else:
        data["conversion_rate"] = 0.0

    # 3. Upsert Profile
    generated_at = datetime.now(timezone.utc)
    await upsert_merchant_profile(session, merchant_id, data, generated_at)
    await record_domain_activity(session, "merchant", merchant_id, "profile", generated_at)


async def generate_shopper_profile_callback(session: AsyncSession, shopper_id: uuid.UUID) -> None:
    """
    Incremental processor callback for regenerating a Shopper Profile.
    Calculates derived metrics and upserts the profile.
    """
    data = await get_shopper_profile_source_data(session, shopper_id)
    
    total_orders = data["total_orders"]
    total_spend = data["total_spend"]
    
    if total_orders > 0:
        data["average_order_value"] = total_spend / total_orders
    else:
        data["average_order_value"] = 0.0

    # Deferred metrics
    data["customer_lifetime_value"] = None
    data["purchase_frequency"] = None
    data["cart_abandonment_count"] = None
    data["lifecycle_stage"] = None
    
    generated_at = datetime.now(timezone.utc)
    await upsert_shopper_profile(session, shopper_id, data, generated_at)
    await record_domain_activity(session, "shopper", shopper_id, "profile", generated_at)


async def get_merchant_profile(session: AsyncSession, merchant_id: uuid.UUID) -> MerchantProfile | None:
    """Retrieve the generated profile for a merchant."""
    return await dal_get_merchant_profile(session, merchant_id)


async def get_shopper_profile(session: AsyncSession, shopper_id: uuid.UUID) -> ShopperProfile | None:
    """Retrieve the generated profile for a shopper."""
    return await dal_get_shopper_profile(session, shopper_id)

